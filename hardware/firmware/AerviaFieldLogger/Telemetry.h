#pragma once
#include <ArduinoJson.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <sys/time.h>
#include <time.h>

uint32_t bootCount=0, txSent=0, txDropped=0;
String deviceId, bootId;
bool clockSynced=false;
const char* clockSource="unavailable";
void queueFieldRecord(JsonDocument&);
bool handleFieldCommand(const char*);
void queueAwsRecord(JsonDocument&);
bool handleAwsCommand(const char*);
int64_t clockSyncAt=0;
char inputCommand[8192];
size_t inputLength=0;
bool receivingCommand=false, commandOverflow=false;

const char* resetLabel(esp_reset_reason_t reason) {
  switch(reason) {
    case ESP_RST_POWERON:return "power_on";
    case ESP_RST_SW:return "software";
    case ESP_RST_PANIC:return "panic";
    case ESP_RST_INT_WDT:return "interrupt_watchdog";
    case ESP_RST_TASK_WDT:return "task_watchdog";
    case ESP_RST_WDT:return "watchdog";
    case ESP_RST_DEEPSLEEP:return "deep_sleep";
    case ESP_RST_BROWNOUT:return "brownout";
    case ESP_RST_EXT:return "external";
    case ESP_RST_USB:return "usb_reset";
    case ESP_RST_JTAG:return "jtag_reset";
    default:return "other_or_unknown";
  }
}
void telemetryBegin() {
  Preferences prefs;
  if(prefs.begin("vbtelemetry",false)) {
    bootCount=prefs.getUInt("boots",0)+1;
    if(prefs.putUInt("boots",bootCount)!=sizeof(uint32_t)) bootCount=0;
    prefs.end();
  }
  char id[24];
  uint64_t mac=ESP.getEfuseMac();
  snprintf(id,sizeof(id),"aervia-%012llx",(unsigned long long)mac);
  deviceId=id;
  snprintf(id,sizeof(id),"%08lx-%08lx",(unsigned long)bootCount,(unsigned long)esp_random());
  bootId=id;
}
// @TIME <Unix epoch milliseconds>\n. Host supplies UTC, no credentials required.
// Existing single-character screen/diagnostic commands are preserved.
bool telemetryCommand(char c) {
  if(!receivingCommand) {
    if(c!='@') return false;
    receivingCommand=true; inputLength=0; commandOverflow=false;return true;
  }
  if(c=='\r')return true;
  if(c=='\n') {
    inputCommand[inputLength]=0;
    if(!commandOverflow && strncmp(inputCommand,"TIME ",5)==0) {
      char* end=nullptr;
      int64_t epoch=strtoll(inputCommand+5,&end,10);
      if(end && *end==0 && epoch>=1704067200000LL && epoch<4102444800000LL) {
        timeval tv={(time_t)(epoch/1000),(suseconds_t)((epoch%1000)*1000)};
        if(settimeofday(&tv,nullptr)==0) {
          clockSynced=true;clockSyncAt=esp_timer_get_time();clockSource="usb_host";
          Serial.println("TIME_SYNC_OK source=usb_host");
        }
      }
    }
    if(!commandOverflow && !handleAwsCommand(inputCommand))handleFieldCommand(inputCommand);
    receivingCommand=false;return true;
  }
  if(inputLength+1<sizeof(inputCommand))inputCommand[inputLength++]=c;
  else commandOverflow=true;
  return true;
}
void finiteValue(JsonDocument& d,const char* name,float value) {
  if(isfinite(value))d[name]=value;else d[name]=nullptr;
}
void emitTelemetry(float pm1,float pm25,float pm4,float pm10,
                   float nc05,float nc1,float nc25,float nc4,float nc10,float size,
                   float temperature,float humidity,float pressure,
                   int32_t voc,int32_t nox,uint16_t rawVoc,uint16_t rawNox,
                   const char* pmState,const char* gasState,bool envValid) {
  JsonDocument d;
  d["type"]="telemetry";d["schema_version"]=2;d["product"]="Aervia";d["thing_name"]="Aervia_sensors";d["timestamp_timezone"]="Asia/Kolkata";
  d["device_id"]=deviceId;d["boot_id"]=bootId;d["sequence"]=live.tick;
  d["timestamp"]=nullptr;
  if(clockSynced) {
    timeval tv; gettimeofday(&tv,nullptr);
    time_t istSeconds=tv.tv_sec+19800; // UTC + 05:30; leave system/NTP time in UTC.
    tm ist;gmtime_r(&istSeconds,&ist);
    char base[32],stamp[40];strftime(base,sizeof(base),"%Y-%m-%dT%H:%M:%S",&ist);
    snprintf(stamp,sizeof(stamp),"%s.%03ld+05:30",base,(long)(tv.tv_usec/1000));
    d["timestamp"]=stamp;
  }
  d["clock_synced"]=clockSynced;
  d["timestamp_source"]=clockSynced?clockSource:"unavailable";
  d["clock_sync_age_s"]=nullptr;
  if(clockSynced)d["clock_sync_age_s"]=(esp_timer_get_time()-clockSyncAt)/1000000.0;
  finiteValue(d,"pm1",pm1);finiteValue(d,"pm2_5",pm25);
  finiteValue(d,"pm4",pm4);finiteValue(d,"pm10",pm10);
  finiteValue(d,"nc0_5",nc05);finiteValue(d,"nc1_0",nc1);
  finiteValue(d,"nc2_5",nc25);finiteValue(d,"nc4",nc4);finiteValue(d,"nc10",nc10);
  finiteValue(d,"typical_particle_size",size);
  finiteValue(d,"temp_c",temperature);finiteValue(d,"humidity_rh",humidity);
  finiteValue(d,"pressure_hpa",pressure);
  d["voc_index"]=nullptr;d["nox_index"]=nullptr;
  if(voc>0)d["voc_index"]=voc;if(nox>0)d["nox_index"]=nox;
  d["sraw_voc"]=nullptr;d["sraw_nox"]=nullptr;
  if(strcmp(gasState,"LEARNING")==0 || strcmp(gasState,"INDEX_WARMUP")==0) {
    d["sraw_voc"]=rawVoc;d["sraw_nox"]=rawNox;
  } else if(strcmp(gasState,"CONDITIONING_NOX_UNAVAILABLE")==0)d["sraw_voc"]=rawVoc;
  d["latitude"]=nullptr;d["longitude"]=nullptr;d["location_source"]="not_configured";
  d["battery_v"]=nullptr;d["battery_pct"]=nullptr;
  d["battery_status"]="no_battery_measurement_hardware";
  d["wifi_rssi"]=nullptr;
  d["wifi_connected"]=WiFi.status()==WL_CONNECTED;
  if(WiFi.status()==WL_CONNECTED)d["wifi_rssi"]=WiFi.RSSI();
  d["transport"]="usb_serial_google_sheets_aws_iot";
  // Completed local writes before this record; delivery is not acknowledged.
  d["packets_sent"]=txSent;d["packets_dropped_local"]=txDropped;
  d["packets_lost"]=nullptr;d["delivery_status"]="unacknowledged";
  d["uptime_s"]=esp_timer_get_time()/1000000.0;
  d["boot_count"]=nullptr;d["restart_count"]=nullptr;
  if(bootCount) {d["boot_count"]=bootCount;d["restart_count"]=bootCount-1;}
  d["boot_reason"]=resetLabel(esp_reset_reason());
  d["boot_reason_code"]=(int)esp_reset_reason();
  JsonObject status=d["sensor_status"].to<JsonObject>();
  status["sps30"]=pmState;status["bme280"]=envValid?"READ_OK":"UNAVAILABLE";
  status["sgp41"]=gasState;
  bool statusFresh=spsInfo.statusValid && (uint32_t)(millis()-spsInfo.statusAt)<15000;
  d["sps30_status_raw"]=nullptr;d["fan_fault"]=nullptr;
  d["laser_fault"]=nullptr;d["fan_speed_warning"]=nullptr;d["status_age_s"]=nullptr;
  if(statusFresh) {
    d["sps30_status_raw"]=spsInfo.status;
    d["fan_fault"]=(bool)(spsInfo.status&(1UL<<4));
    d["laser_fault"]=(bool)(spsInfo.status&(1UL<<5));
    d["fan_speed_warning"]=(bool)(spsInfo.status&(1UL<<21));
    d["status_age_s"]=(uint32_t)(millis()-spsInfo.statusAt)/1000.0;
  }
  JsonArray flags=d["quality_flags"].to<JsonArray>();
  if(!clockSynced)flags.add("clock_unsynced");
  if(!isfinite(pm25))flags.add("pm_missing");
  if(!envValid)flags.add("environment_missing");
  if(voc<=0 || nox<=0)flags.add("gas_not_ready");
  if(strcmp(pmState,"SETTLING")==0)flags.add("pm_settling");
  if(!statusFresh)flags.add("pm_status_unavailable");
  if(statusFresh && (spsInfo.status&((1UL<<4)|(1UL<<5)|(1UL<<21))))flags.add("pm_sensor_fault");
  if(envValid && humidity>80)flags.add("high_humidity_review_required");
  d["quality_flag"]=flags.size()?"review":"ok";
  d["quality_scope"]="availability_warmup_status_humidity_clock;not_spike_or_flatline_detection";
  snprintf(telemetryScreen.timestamp,sizeof(telemetryScreen.timestamp),"%s",
           clockSynced?d["timestamp"].as<const char*>():"Waiting for network time");
  telemetryScreen.uptime=esp_timer_get_time()/1000000.0;
  telemetryScreen.boots=bootCount;telemetryScreen.sent=txSent;telemetryScreen.dropped=txDropped;
  telemetryScreen.rawVoc=rawVoc;telemetryScreen.rawNox=rawNox;
  telemetryScreen.rawVocValid=!strcmp(gasState,"LEARNING") || !strcmp(gasState,"INDEX_WARMUP") || !strcmp(gasState,"CONDITIONING_NOX_UNAVAILABLE");
  telemetryScreen.rawNoxValid=!strcmp(gasState,"LEARNING") || !strcmp(gasState,"INDEX_WARMUP");
  telemetryScreen.clockSynced=clockSynced;telemetryScreen.reset=resetLabel(esp_reset_reason());
  telemetryScreen.device=deviceId;telemetryScreen.session=bootId;telemetryScreen.quality=flags.size()?"REVIEW FLAGS":"OK";
  telemetryScreen.highHumidity=envValid && humidity>80;
  queueFieldRecord(d);
  queueAwsRecord(d);
  char output[4096];
  size_t needed=measureJson(d);
  if(needed+2>sizeof(output)) {++txDropped;return;}
  size_t n=serializeJson(d,output,sizeof(output));output[n++]='\n';
  if(Serial.availableForWrite()<(int)n) {++txDropped;return;}
  if(Serial.write((const uint8_t*)output,n)==n)++txSent;else ++txDropped;
}
