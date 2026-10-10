#include <Arduino.h>
#include <Wire.h>
#include <driver/gpio.h>
#include <SensirionI2cSps30.h>
#include <SensirionI2CSgp41.h>
#include <VOCGasIndexAlgorithm.h>
#include <NOxGasIndexAlgorithm.h>
#include <Adafruit_BME280.h>
#include <math.h>
#include <WiFi.h>
#include <esp_heap_caps.h>
#include "DisplayUI.h"
#include "Telemetry.h"
#include "FieldLogger.h"
#include "AwsLogger.h"

TwoWire environmentBus(1);
SensirionI2cSps30 sps;
SensirionI2CSgp41 sgp;
Adafruit_BME280 bme;
VOCGasIndexAlgorithm vocAlgorithm;
NOxGasIndexAlgorithm noxAlgorithm;
bool spsStarted = false, bmePresent = false, sgpPresent = false;
bool environmentBusReady = false;
uint32_t nextEnvironmentRetry = 0;
int8_t spsSerial[32] = {0};
uint16_t sgpSerial[3] = {0};
uint16_t sgpSelfTest = 0;
uint8_t bmeAddress = 0;
uint8_t conditioningRemaining = 10;
uint32_t nextTick = 0, tick = 0;

void report(const char* operation, int16_t error) {
  char text[100] = {0};
  if (error) errorToString(error, text, sizeof(text));
  Serial.printf("COMMAND %s error=%d %s\n", operation, (int)error, text);
}

bool probe(TwoWire& bus, uint8_t address) {
  bus.beginTransmission(address);
  return bus.endTransmission() == 0;
}

void scan(TwoWire& bus, const char* name) {
  unsigned count = 0;
  for (uint8_t address = 1; address < 127; ++address) {
    if (probe(bus, address)) {
      Serial.printf("ACK bus=%s address=0x%02X\n", name, address);
      ++count;
    }
  }
  Serial.printf("SCAN bus=%s devices=%u\n", name, count);
}

void summary() {
  Serial.printf("SUMMARY SPS30=%s bus=1/2 serial=%s BME280=%s bus=8/9 address=0x%02X SGP41=%s bus=8/9 serial=%04X%04X%04X selftest=0x%04X\n",
                spsStarted ? "STARTED" : "UNAVAILABLE", (char*)spsSerial,
                bmePresent ? "FOUND" : "UNAVAILABLE", bmeAddress,
                sgpPresent ? "FOUND" : "UNAVAILABLE", sgpSerial[0], sgpSerial[1],
                sgpSerial[2], sgpSelfTest);
}

void diagnoseEnvironment() {
  Serial.printf("ENV_BUS ready=%u sda_pin=8 level=%d scl_pin=9 level=%d\n",
                environmentBusReady,digitalRead(8),digitalRead(9));
  if (!environmentBusReady) return;
  for (uint8_t address : {uint8_t(0x76),uint8_t(0x77),uint8_t(0x59)}) {
    environmentBus.beginTransmission(address);
    uint8_t result = environmentBus.endTransmission();
    Serial.printf("ENV_PROBE address=0x%02X result=%u\n",address,result);
  }
}

void initializeEnvironment() {
  if (environmentBusReady) {
    if (!bmePresent) for (uint8_t address : {uint8_t(0x76), uint8_t(0x77)}) {
      if (probe(environmentBus, address) && bme.begin(address, &environmentBus)) {
        bmePresent = true; bmeAddress = address;
        Serial.printf("BME280_INIT_OK address=0x%02X chip_id=0x%02lX\n",
                      address, (unsigned long)bme.sensorID());
        break;
      }
    }
    if (!sgpPresent && probe(environmentBus, 0x59)) {
      sgp.begin(environmentBus);
      uint16_t error = sgp.getSerialNumber(sgpSerial);
      report("SGP41_SERIAL", error);
      if (!error) {
        error = sgp.executeSelfTest(sgpSelfTest);
        report("SGP41_SELFTEST", error);
        sgpPresent = !error && sgpSelfTest == 0xD400;
        if (sgpPresent) conditioningRemaining = 10;
      }
    }
  }
}

void trendTiming() {
  unsigned valid=0, intervals=0;
  uint32_t minimum=UINT32_MAX, maximum=0; double total=0;
  unsigned begin=history.size()>60?history.size()-60:0;
  for(unsigned i=begin;i<history.size();++i) {
    if(isfinite(history.at(i).pm25)) ++valid;
    if(i>begin) {
      uint32_t dt=history.at(i).ms-history.at(i-1).ms;
      if(dt<minimum) minimum=dt;
      if(dt>maximum) maximum=dt;
      total+=dt; ++intervals;
    }
  }
  Serial.printf("TREND_TIMING samples=%u valid_recent=%u intervals=%u min_ms=%lu mean_ms=%.1f max_ms=%lu frames=%lu last_frame_ms=%lu\n",
                history.size(),valid,intervals,(unsigned long)(intervals?minimum:0),
                intervals?total/intervals:0,(unsigned long)maximum,
                (unsigned long)frameCount,(unsigned long)lastFrameMs);
}

void setup() {
  Serial.setTxBufferSize(8192);
  Serial.setRxBufferSize(8192);
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0); // Debug logging must never hold up sensing/UI.

  telemetryBegin();
  fieldBegin();
  awsBegin();
  delay(100);
  displayStartup();
  Serial.println("AERVIA_FIELD_LOGGER 2026-10-08 button=6 pages=8 internal_pullups=enabled cloud=google_sheets_and_aws_iot");
  bool pmBusOK = Wire.begin(1, 2, 100000);
  bool envBusOK = environmentBus.begin(8, 9, 100000);
  environmentBusReady = envBusOK;
  Wire.setTimeOut(50);
  environmentBus.setTimeOut(50);
  gpio_pullup_en(GPIO_NUM_1); gpio_pullup_en(GPIO_NUM_2);
  gpio_pullup_en(GPIO_NUM_8); gpio_pullup_en(GPIO_NUM_9);
  Serial.printf("BUS_INIT pm=%u env=%u\n", pmBusOK, envBusOK);


  if (pmBusOK && probe(Wire, 0x69)) {
    sps.begin(Wire, SPS30_I2C_ADDR_69);
    int16_t error = sps.stopMeasurement();
    report("SPS30_STOP", error);
    if (!error) {
      delay(100);
      error = sps.readSerialNumber(spsSerial, sizeof(spsSerial));
      report("SPS30_SERIAL", error);
      spsSerial[31] = 0;
      if (!error) {
        spsInfo.firmwareValid = !sps.readFirmwareVersion(spsInfo.major, spsInfo.minor);
        spsInfo.cleaningValid = !sps.readAutoCleaningInterval(spsInfo.cleanSeconds);
        int16_t productError = sps.readProductType(spsInfo.product, sizeof(spsInfo.product));
        report("SPS30_PRODUCT", productError);
        spsInfo.product[sizeof(spsInfo.product)-1] = 0;
        if(productError) spsInfo.product[0] = 0;
        Serial.printf("SPS30_META fw_valid=%u fw=%u.%u cleaning_valid=%u interval_s=%lu product=%s\n",
                      spsInfo.firmwareValid,spsInfo.major,spsInfo.minor,spsInfo.cleaningValid,
                      (unsigned long)spsInfo.cleanSeconds,(char*)spsInfo.product);
        error = sps.startMeasurement(SPS30_OUTPUT_FORMAT_OUTPUT_FORMAT_FLOAT);
        report("SPS30_START", error);
        spsStarted = !error;
      }
    }
  }
  diagnoseEnvironment();
  initializeEnvironment();
  nextEnvironmentRetry = millis() + 5000;
  summary();
  renderPage((char*)spsSerial);
  nextTick = millis() + 1000;
}

void loop() {
  fieldLoop();
  handleButton((char*)spsSerial);
  while (Serial.available()) {
    char command = Serial.read();
    if (telemetryCommand(command)) continue;
    if (command == 'i') summary();
    if (command == 't') trendTiming();
    if (command == 'd') { diagnoseEnvironment(); initializeEnvironment(); summary(); }
    // Serial page switching permits bench checks before the physical button is connected.
    if (command >= '1' && command <= '8') {
      page = command - '1'; renderPage((char*)spsSerial);
      Serial.printf("PAGE serial=%u\n",page+1);
    }
  }
  uint32_t now = millis();
  if ((int32_t)(now - nextTick) < 0) { delay(1); return; }
  nextTick += 1000;
  if ((int32_t)(now - nextTick) >= 0) {
    Serial.println("TIMING_GAP gas_indices_require_regular_cadence");
    nextTick = now + 1000;
  }
  ++tick;
  if (environmentBusReady && (!bmePresent || !sgpPresent) &&
      (int32_t)(now - nextEnvironmentRetry) >= 0) {
    nextEnvironmentRetry = now + 5000;
    diagnoseEnvironment(); initializeEnvironment();
  }
  float temperature = NAN, humidity = NAN, pressure = NAN;
  bool envValid = false;
  if (bmePresent) {
    temperature = bme.readTemperature();
    humidity = bme.readHumidity();
    pressure = bme.readPressure() / 100.0f;
    envValid = isfinite(temperature) && isfinite(humidity) && isfinite(pressure)
               && humidity >= 0 && humidity <= 100 && temperature >= -40 && temperature <= 85;
    if (!envValid) temperature = humidity = pressure = NAN;
  }
  float pm1 = NAN, pm25 = NAN, pm4 = NAN, pm10 = NAN;
  float nc05=NAN, nc1=NAN, nc25=NAN, nc4=NAN, nc10=NAN, size=NAN;
  const char* pmState = "UNAVAILABLE";
  if (spsStarted) {
    uint16_t ready = 0;
    int16_t error = sps.readDataReadyFlag(ready);
    if (error) { report("SPS30_READY", error); pmState = "ERROR"; }
    else if (ready == 1) {
      error = sps.readMeasurementValuesFloat(pm1, pm25, pm4, pm10,
                                            nc05, nc1, nc25, nc4, nc10, size);
      if (error || !isfinite(pm1) || !isfinite(pm25) || !isfinite(pm4) || !isfinite(pm10) ||
          !isfinite(nc05) || !isfinite(nc1) || !isfinite(nc25) ||
          !isfinite(nc4) || !isfinite(nc10) || !isfinite(size)) {
        report("SPS30_READ", error); pmState = "ERROR";
        pm1 = pm25 = pm4 = pm10 = NAN;
        nc05 = nc1 = nc25 = nc4 = nc10 = size = NAN;
      } else pmState = tick < 60 ? "SETTLING" : "READ_OK";
    } else pmState = "NOT_READY";
  }
  uint16_t rawVoc = 0, rawNox = 0;
  int32_t vocIndex = -1, noxIndex = -1;
  const char* gasState = "UNAVAILABLE";
  if (sgpPresent) {
    uint16_t rhTicks = envValid ? (uint16_t)lroundf(humidity * 65535.0f / 100.0f) : 0x8000;
    uint16_t tTicks = envValid ? (uint16_t)lroundf((temperature + 45.0f) * 65535.0f / 175.0f) : 0x6666;
    uint16_t error;
    if (conditioningRemaining) {
      error = sgp.executeConditioning(rhTicks, tTicks, rawVoc);
      gasState = "CONDITIONING_NOX_UNAVAILABLE";
      if (!error) --conditioningRemaining;
    } else {
      error = sgp.measureRawSignals(rhTicks, tTicks, rawVoc, rawNox);
      gasState = "LEARNING";
      if (!error) {
        vocIndex = vocAlgorithm.process(rawVoc);
        noxIndex = noxAlgorithm.process(rawNox);
        if (vocIndex == 0 || noxIndex == 0) gasState = "INDEX_WARMUP";
      }
    }
    if (error) { report("SGP41_READ", error); gasState = "ERROR"; rawVoc = rawNox = 0; }
  }
  Serial.printf("READING tick=%lu uptime_ms=%lu pm_state=%s pm1=%.3f pm25=%.3f pm4=%.3f pm10=%.3f temp_c=%.2f rh_pct=%.2f pressure_hpa=%.2f env_state=%s gas_state=%s compensation=%s sraw_voc=%u sraw_nox=%u voc_index=%ld nox_index=%ld\n",
                (unsigned long)tick, (unsigned long)now, pmState, pm1, pm25, pm4, pm10,
                temperature, humidity, pressure, envValid ? "READ_OK" : "UNAVAILABLE",
                gasState, envValid ? "BME280" : "DEFAULT_25C_50RH", rawVoc, rawNox,
                (long)vocIndex, (long)noxIndex);
  live.pm[0]=pm1; live.pm[1]=pm25; live.pm[2]=pm4; live.pm[3]=pm10;
  live.number[0]=nc05; live.number[1]=nc1; live.number[2]=nc25;
  live.number[3]=nc4; live.number[4]=nc10; live.particleSize=size;
  live.temperature=temperature; live.humidity=humidity; live.pressure=pressure;
  live.envValid=envValid; live.voc=vocIndex; live.nox=noxIndex;
  live.pmState=pmState; live.gasState=gasState; live.tick=tick; live.sampledAt=now;
  // A not-ready poll is not a measurement and must not erase a valid trace.
  // Actual read errors still insert a missing-data marker and break the line.
  if(strcmp(pmState,"NOT_READY")!=0) history.add(now,pm25,pm10);
  Serial.printf("SPS30_ALL nc05=%.3f nc1=%.3f nc25=%.3f nc4=%.3f nc10=%.3f size_um=%.3f\n",
                nc05,nc1,nc25,nc4,nc10,size);
  if ((tick == 1 || tick % 10 == 0) && spsStarted) {
    uint32_t status = 0;
    int16_t error = sps.readDeviceStatusRegister(status);
    report("SPS30_STATUS", error);
    spsInfo.statusValid = !error;
    if(!error) { spsInfo.status=status; spsInfo.statusAt=millis(); }
    if (!error) Serial.printf("SPS30_STATUS raw=0x%08lX fan_fault=%u laser_fault=%u speed_warning=%u\n",
                              (unsigned long)status, !!(status & (1UL << 4)),
                              !!(status & (1UL << 5)), !!(status & (1UL << 21)));
  }
  emitTelemetry(pm1,pm25,pm4,pm10,nc05,nc1,nc25,nc4,nc10,size,
                temperature,humidity,pressure,vocIndex,noxIndex,rawVoc,rawNox,
                pmState,gasState,envValid);
  renderPage((char*)spsSerial);
  if (tick % 15 == 0) summary();
}
