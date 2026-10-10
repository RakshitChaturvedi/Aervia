#pragma once
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>
#include <Fonts/FreeSansBold18pt7b.h>
#include "History.h"
#include "GraphScale.h"

constexpr int TFT_CS = 10, TFT_DC = 4, TFT_RST = 5;
constexpr int TFT_MOSI = 11, TFT_SCK = 12, BUTTON_PIN = 6;
Adafruit_ILI9341 tft(&SPI, TFT_DC, TFT_CS, TFT_RST);
class FieldCanvas : public GFXcanvas16 {
 public:
 FieldCanvas():GFXcanvas16(320,240,false){}
 bool allocate() {
  if(buffer)return true;
  buffer=(uint16_t*)heap_caps_calloc(320*240,sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
  if(!buffer)buffer=(uint16_t*)heap_caps_calloc(320*240,sizeof(uint16_t),MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
  return buffer!=nullptr;
 }
};
FieldCanvas canvas;
TrendHistory history;
PageButton pageButton;
const char* cloudState="Starting logger";
volatile uint32_t cloudQueued=0,cloudUploaded=0,cloudDropped=0;
volatile int cloudHttpCode=0;
const char* awsState="AWS setup needed";
volatile bool awsConnected=false;
volatile uint32_t awsAcknowledged=0,awsQueued=0,awsDropped=0;
volatile int awsError=0,awsConnack=0;
constexpr unsigned PAGE_COUNT=8;
uint8_t page = 0;
struct TelemetryScreen {
  char timestamp[40]="Waiting for network time";
  double uptime=0;
  uint32_t boots=0,sent=0,dropped=0;
  uint16_t rawVoc=0,rawNox=0;
  bool rawVocValid=false,rawNoxValid=false,clockSynced=false,highHumidity=false;
  const char* reset="starting";
  const char* quality="STARTING";
  String device,session;
} telemetryScreen;
bool displayAvailable = false;
uint32_t frameCount=0, lastFrameMs=0;
const uint16_t BG = 0x0843, CARD = 0x10C6, WHITE = 0xF7BE,
               MUTED = 0x94B4, ACCENT = 0x3E9F, MINT = 0x5F33, AMBER = 0xFDAD;
struct LiveData {
  float pm[4] = {NAN,NAN,NAN,NAN};
  float number[5] = {NAN,NAN,NAN,NAN,NAN};
  float particleSize = NAN, temperature = NAN, humidity = NAN, pressure = NAN;
  int32_t voc = -1, nox = -1;
  const char* pmState = "STARTING";
  const char* gasState = "STARTING";
  bool envValid = false;
  uint32_t tick = 0, sampledAt = 0;
} live;
struct SpsInfo {
  uint8_t major = 0, minor = 0;
  uint32_t cleanSeconds = 0, status = 0, statusAt = 0;
  bool firmwareValid = false, cleaningValid = false, statusValid = false;
  int8_t product[16] = {0};
} spsInfo;

void text(int x, int baseline, const char* s, const GFXfont* font = &FreeSans9pt7b,
          uint16_t colour = WHITE) {
  canvas.setFont(font); canvas.setTextSize(1); canvas.setTextColor(colour);
  canvas.setCursor(x, baseline); canvas.print(s);
}
void small(int x, int y, const char* s, uint16_t colour = MUTED) {
  canvas.setFont(nullptr); canvas.setTextSize(1); canvas.setTextColor(colour);
  canvas.setCursor(x,y); canvas.print(s);
}
void value(char* out, size_t n, float v, unsigned decimals = 1) {
  if (isfinite(v)) snprintf(out,n,"%.*f",int(decimals),v);
  else snprintf(out,n,"--");
}
void rightText(int right, int baseline, const char* s,
               const GFXfont* font = &FreeSansBold9pt7b, uint16_t colour = WHITE) {
  canvas.setFont(font); int16_t x,y; uint16_t w,h;
  canvas.getTextBounds(s,0,baseline,&x,&y,&w,&h);
  text(right - int(w) - x,baseline,s,font,colour);
}
void showFrame() {
  if (displayAvailable) {
    uint32_t start=millis();
    tft.drawRGBBitmap(0,0,canvas.getBuffer(),320,240);
    lastFrameMs=millis()-start; ++frameCount;
  }
}
void frame(const char* title, const char* subtitle) {
  canvas.fillScreen(BG);
  text(10,21,title,&FreeSansBold9pt7b);
  small(10,28,subtitle);
  char counter[8]; snprintf(counter,sizeof(counter),"%u/7",page+1);
  small(290,12,counter,ACCENT);
  canvas.drawFastHLine(8,222,304,CARD);
  small(10,230,"Press: next  Hold: home");
  for(int i=0;i<PAGE_COUNT;++i) canvas.fillCircle(235+i*10,233,2,i==page?ACCENT:CARD);
}
void metric(int x, const char* title, const char* reading, const char* unit,
            uint16_t colour = WHITE) {
  canvas.fillRoundRect(x,137,72,64,6,CARD);
  small(x+7,145,title);
  text(x+7,176,reading,&FreeSansBold9pt7b,colour);
  small(x+7,187,unit);
}
void overview() {
  frame("Aervia", "ROOM OVERVIEW  |  LIVE, 1 SECOND");
  canvas.fillRoundRect(8,42,188,86,7,CARD);
  canvas.fillRoundRect(202,42,110,86,7,CARD);
  text(18,63,"PM2.5",&FreeSans9pt7b,ACCENT);
  char s[48]; value(s,sizeof(s),live.pm[1]);
  // Smaller font accommodates exceptional readings without overflowing.
  text(18,105,s,strlen(s)>5?&FreeSansBold12pt7b:&FreeSansBold18pt7b);
  small(18,115,"ug/m3 | live concentration");
  text(212,63,"PM10",&FreeSans9pt7b,MINT);
  value(s,sizeof(s),live.pm[3]);
  rightText(302,96,s,&FreeSansBold12pt7b);
  small(212,115,"ug/m3");
  value(s,sizeof(s),live.temperature); metric(8,"TEMP",s,"Celsius");
  value(s,sizeof(s),live.humidity); metric(86,"HUMIDITY",s,"% RH");
  if(live.voc>0) snprintf(s,sizeof(s),"%ld",(long)live.voc);
  else snprintf(s,sizeof(s),"%s",strcmp(live.gasState,"ERROR")==0?"Error":
       strcmp(live.gasState,"UNAVAILABLE")==0?"--":"Wait");
  metric(164,"VOC",s,"Index");
  if(live.nox>0) snprintf(s,sizeof(s),"%ld",(long)live.nox);
  else snprintf(s,sizeof(s),"%s",strcmp(live.gasState,"ERROR")==0?"Error":
       strcmp(live.gasState,"UNAVAILABLE")==0?"--":"Wait");
  metric(242,"NOx",s,"Index");
  if(isfinite(live.pressure)) snprintf(s,sizeof(s),"Pressure %.1f hPa",live.pressure);
  else snprintf(s,sizeof(s),"Pressure --");
  small(10,209,s);
  const char* status = !isfinite(live.pm[1]) ? "PM unavailable" :
                      !strcmp(live.pmState,"SETTLING") ? "PM settling" :
                      (live.voc<=0 || live.nox<=0) ? "Gas warming up" : "Gas learning";
  if(strcmp(live.gasState,"ERROR")==0) status="Gas read error";
  else if(strcmp(live.gasState,"UNAVAILABLE")==0) status="Gas unavailable";
  small(206,209,status,AMBER);
}
void particles(const char* serial) {
  frame("Particle lab", "SPS30  |  ALL 10 MEASUREMENT OUTPUTS");
  canvas.fillRoundRect(8,42,148,135,6,CARD);
  canvas.fillRoundRect(164,42,148,135,6,CARD);
  small(15,49,"MASS  ug/m3",ACCENT);
  small(171,49,"um BIN | #/cm3",MINT);
  const char* massLabels[]={"PM1","PM2.5","PM4","PM10"};
  const char* countLabels[]={"0.3-0.5","0.3-1","0.3-2.5","0.3-4","0.3-10"};
  char s[64];
  for(int i=0;i<4;++i) {
    int y=76+i*24; small(15,y-9,massLabels[i],WHITE);
    value(s,sizeof(s),live.pm[i]); rightText(149,y,s);
  }
  for(int i=0;i<5;++i) {
    int y=76+i*24; small(171,y-9,countLabels[i],WHITE);
    value(s,sizeof(s),live.number[i]); rightText(305,y,s);
  }
  if(isfinite(live.particleSize)) snprintf(s,sizeof(s),"Size %.3f um",live.particleSize);
  else snprintf(s,sizeof(s),"Size -- um");
  small(15,163,s,ACCENT);
  snprintf(s,sizeof(s),"ID %s  SN %s",spsInfo.product[0]?(char*)spsInfo.product:"--",serial[0]?serial:"--");
  small(10,184,s);
  char fw[12],clean[16];
  if(spsInfo.firmwareValid) snprintf(fw,sizeof(fw),"%u.%u",spsInfo.major,spsInfo.minor);
  else snprintf(fw,sizeof(fw),"--");
  if(spsInfo.cleaningValid) snprintf(clean,sizeof(clean),"%lus",(unsigned long)spsInfo.cleanSeconds);
  else snprintf(clean,sizeof(clean),"--");
  snprintf(s,sizeof(s),"FW %s   Auto-clean interval %s",fw,clean);
  small(10,196,s);
  if(!spsInfo.statusValid || uint32_t(millis()-spsInfo.statusAt)>15000)
    snprintf(s,sizeof(s),"Status unavailable | %s",live.pmState);
  else snprintf(s,sizeof(s),"Status %08lX | %s | %s",(unsigned long)spsInfo.status,
       spsInfo.status ? "CHECK SENSOR" : "NO FAULTS",live.pmState);
  small(10,208,s,spsInfo.status?AMBER:MUTED);
}
void trend(uint32_t now) {
  frame("Live trend", "AUTO SCALE  |  1 SECOND SAMPLES  |  ug/m3");
  char s[64],a[16],b[16]; value(a,sizeof(a),live.pm[1]); value(b,sizeof(b),live.pm[3]);
  snprintf(s,sizeof(s),"PM2.5 %s",a); small(40,48,s,ACCENT);
  snprintf(s,sizeof(s),"PM10 %s",b); small(193,48,s,MINT);
  constexpr int left=40, top=67, width=268, height=115;
  const GraphScale axis=graphScale(history,now);
  if(axis.valid) {
    int intervals=int(lroundf((axis.upper-axis.lower)/axis.step));
    int decimals=axis.step>=1?0:axis.step>=0.1f?1:2;
    for(int i=0;i<=intervals;++i) {
      float v=axis.upper-i*axis.step;
      int y=top+int(lroundf((axis.upper-v)*(height-1)/(axis.upper-axis.lower)));
      canvas.drawFastHLine(left,y,width,CARD);
      snprintf(s,sizeof(s),"%.*f",decimals,v); small(4,y-3,s);
    }
  } else {
    small(80,115,"Waiting for live measurements");
  }
  for(int i=0;i<=2;++i) canvas.drawFastVLine(left+i*(width-1)/2,top,height,CARD);
  canvas.drawFastHLine(left,top+height-1,width,MUTED);
  canvas.drawFastVLine(left,top,height,MUTED);
  // Multiple samples can occupy one column; drawing every segment preserves peaks.
  // No invented samples and no line across missing readings or timing gaps.
  for(int trace=0;trace<2;++trace) {
    bool previous=false; int px=0,py=0; uint32_t previousTime=0;
    for(unsigned i=0;i<history.size();++i) {
      const auto& p=history.at(i); uint32_t age=now-p.ms;
      float v=trace==0?p.pm10:p.pm25;
      if(!axis.valid || age>axis.spanMs || !isfinite(v) || v<0) { previous=false; continue; }
      int x=left+int((axis.spanMs-age)*(width-1)/axis.spanMs);
      int y=top+height-1-int((v-axis.lower)*(height-1)/(axis.upper-axis.lower));
      uint16_t colour=trace==0?MINT:ACCENT;
      if(previous && uint32_t(p.ms-previousTime)<=2500) {
        canvas.drawLine(px,py,x,y,colour);
        canvas.drawLine(px,min(py+1,top+height-1),x,min(y+1,top+height-1),colour);
      }
      else canvas.drawPixel(x,y,colour);
      px=x; py=y; previousTime=p.ms; previous=true;
    }
  }
  for(int i=0;i<2;++i) {
    uint32_t seconds=(axis.spanMs/(i+1))/1000;
    if(seconds<60) snprintf(s,sizeof(s),"-%lus",(unsigned long)seconds);
    else if(seconds%60) snprintf(s,sizeof(s),"-%lum%lus",(unsigned long)(seconds/60),(unsigned long)(seconds%60));
    else snprintf(s,sizeof(s),"-%lum",(unsigned long)(seconds/60));
    small(i==0?40:165,186,s);
  }
  small(290,186,"Now");
  float low,mean,high,change;
  if(history.stats(now,low,mean,high)) snprintf(s,sizeof(s),"PM2.5 MIN %.1f  AVG %.1f  MAX %.1f",low,mean,high);
  else snprintf(s,sizeof(s),"Waiting for particle readings");
  small(10,200,s);
  if(history.delta(now,change)) snprintf(s,sizeof(s),"%s  %+.1f ug/m3 / previous 30s",
       change>1?"RISING":change< -1?"FALLING":"STEADY",change);
  else snprintf(s,sizeof(s),"Building history | real readings only");
  small(10,211,s,ACCENT);
}
// Details use compact, aligned rows: real values or explicit unavailable reasons.
void detailRow(unsigned row,const char* label,const char* reading,uint16_t colour=WHITE) {
  int y=48+row*17;
  if(row%2==0)canvas.fillRect(8,y-4,304,16,CARD);
  small(12,y,label,MUTED);
  small(max(125,308-int(strlen(reading))*6),y,reading,colour);
}
void environmentDetails() {
  frame("Environment", "BME280 + SGP41  |  MEASURED / DERIVED");
  char s[48];
  value(s,sizeof(s),live.temperature,2);detailRow(0,"Temperature C",s);
  value(s,sizeof(s),live.humidity,2);detailRow(1,"Humidity % RH",s);
  value(s,sizeof(s),live.pressure,2);detailRow(2,"Pressure hPa",s);
  if(live.voc>0)snprintf(s,sizeof(s),"%ld",(long)live.voc);else strcpy(s,"Not ready");
  detailRow(3,"VOC index",s,ACCENT);
  if(live.nox>0)snprintf(s,sizeof(s),"%ld",(long)live.nox);else strcpy(s,"Not ready");
  detailRow(4,"NOx index",s,MINT);
  if(telemetryScreen.rawVocValid)snprintf(s,sizeof(s),"%u",telemetryScreen.rawVoc);else strcpy(s,"Unavailable");
  detailRow(5,"VOC raw ticks",s);
  if(telemetryScreen.rawNoxValid)snprintf(s,sizeof(s),"%u",telemetryScreen.rawNox);else strcpy(s,"Unavailable");
  detailRow(6,"NOx raw ticks",s);
  detailRow(7,"Compensation",live.envValid?"BME280":"Default 25C/50%",live.envValid?WHITE:AMBER);
  small(12,190,"Gas state:",MUTED);small(12,203,live.gasState,AMBER);
}
void deviceDetails() {
  frame("Device telemetry", "DEVICE STATUS  |  UTC CLOCK");
  small(12,46,"UTC sample timestamp",MUTED);small(12,60,telemetryScreen.timestamp,ACCENT);
  char s[48];snprintf(s,sizeof(s),"%.0f",telemetryScreen.uptime);detailRow(2,"Uptime seconds",s);
  snprintf(s,sizeof(s),"%lu",(unsigned long)(telemetryScreen.boots?telemetryScreen.boots-1:0));
  detailRow(3,"Restarts*",telemetryScreen.boots?s:"Unavailable");
  detailRow(4,"Boot reason",telemetryScreen.reset);
  snprintf(s,sizeof(s),"%lu",(unsigned long)telemetryScreen.sent);detailRow(5,"Packets sent",s);
  snprintf(s,sizeof(s),"%lu",(unsigned long)telemetryScreen.dropped);detailRow(6,"Local drops",s);
  detailRow(7,"Packets lost","Unknown: no ACK",AMBER);
  if(WiFi.status()==WL_CONNECTED)snprintf(s,sizeof(s),"%d dBm",WiFi.RSSI());else strcpy(s,"Disconnected");
  detailRow(8,"Wi-Fi RSSI",s);
  small(12,207,"*Since telemetry counter initialized",MUTED);
}
void healthDetails() {
  frame("Health & context", "NO PLACEHOLDER MEASUREMENTS");
  detailRow(0,"Latitude","-- not configured");
  detailRow(1,"Longitude","-- not configured");
  detailRow(2,"Battery V / %","-- no measurement");
  bool fresh=spsInfo.statusValid && uint32_t(millis()-spsInfo.statusAt)<15000;
  detailRow(3,"Fan fault",fresh?(spsInfo.status&(1UL<<4)?"YES":"NO"):"Unavailable");
  detailRow(4,"Laser fault",fresh?(spsInfo.status&(1UL<<5)?"YES":"NO"):"Unavailable");
  detailRow(5,"Fan speed",fresh?(spsInfo.status&(1UL<<21)?"WARNING":"OK"):"Unavailable");
  detailRow(6,"Quality",telemetryScreen.quality,AMBER);
  detailRow(7,"PM state",live.pmState);
  detailRow(8,"BME280",live.envValid?"READ OK":"Unavailable");
  small(12,205,telemetryScreen.highHumidity?"High RH: review PM reliability":
        !telemetryScreen.clockSynced?"Clock not synced: check Wi-Fi":
        live.voc<=0 || live.nox<=0?"Gas warm-up: indices unavailable":"Spike/flatline checks: not assessed",AMBER);
}
void loggingDetails() {
 frame("Field logger", "GOOGLE SHEETS  |  NEW TAB PER BOOT");
 char s[48];
 small(12,48,"Upload state",MUTED);small(12,64,cloudState,ACCENT);
 detailRow(2,"Wi-Fi",WiFi.status()==WL_CONNECTED?"Connected":"Disconnected");
 detailRow(3,"IST clock",telemetryScreen.clockSynced?"Synced":"Waiting for NTP");
 snprintf(s,sizeof(s),"%lu",(unsigned long)cloudQueued);detailRow(4,"Queued samples",s);
 snprintf(s,sizeof(s),"%lu",(unsigned long)cloudUploaded);detailRow(5,"Uploaded",s,MINT);
 snprintf(s,sizeof(s),"%lu",(unsigned long)cloudDropped);detailRow(6,"Storage drops",s,cloudDropped?AMBER:WHITE);
 snprintf(s,sizeof(s),"%d",cloudHttpCode);detailRow(7,"Last HTTP code",s);
 small(12,190,"Tab session:",MUTED);small(12,203,telemetryScreen.session.c_str());
}
void awsDetails() {
 frame("Aervia cloud", "AWS IOT CORE  |  MQTT TLS  |  QOS 1");
 char s[48];small(12,48,"AWS status",MUTED);small(12,64,awsState,awsConnected?MINT:AMBER);
 detailRow(2,"Wi-Fi",WiFi.status()==WL_CONNECTED?"Connected":"Disconnected");
 detailRow(3,"IST clock",telemetryScreen.clockSynced?"Synced":"Waiting for NTP");
 snprintf(s,sizeof(s),"%lu",(unsigned long)awsAcknowledged);detailRow(4,"AWS acknowledged",s,MINT);
 snprintf(s,sizeof(s),"%lu",(unsigned long)awsQueued);detailRow(5,"AWS pending",s);
 snprintf(s,sizeof(s),"%lu",(unsigned long)awsDropped);detailRow(6,"AWS buffer drops",s,awsDropped?AMBER:WHITE);
 snprintf(s,sizeof(s),"%d / %d",(int)awsError,(int)awsConnack);detailRow(7,"Error / CONNACK",s);
 small(12,191,"Device: Aervia_sensors",MUTED);small(12,207,"Sheets status on previous page",MUTED);
}
void renderPage(const char* serial) {
  if(!displayAvailable) return;
  if(page==0) overview(); else if(page==1) particles(serial); else if(page==2) trend(millis());
  else if(page==3) environmentDetails(); else if(page==4) deviceDetails(); else if(page==5) healthDetails(); else if(page==6) loggingDetails(); else awsDetails();
  showFrame();
}
void handleButton(const char* serial) {
  auto event=pageButton.update(digitalRead(BUTTON_PIN)==LOW,millis());
  if(event==PageButton::None) return;
  if(event==PageButton::Home) page=0; else page=(page+1)%PAGE_COUNT;
  Serial.printf("BUTTON action=%s page=%u\n",event==PageButton::Home?"HOME":"NEXT",page+1);
  renderPage(serial);
}
void displayStartup() {
  pinMode(BUTTON_PIN,INPUT_PULLUP);
  SPI.begin(TFT_SCK,-1,TFT_MOSI,TFT_CS); tft.begin(10000000); tft.setRotation(3);
  canvas.allocate();canvas.setTextWrap(false); displayAvailable=canvas.getBuffer()!=nullptr;
  if(!displayAvailable) { Serial.println("DISPLAY_ERROR framebuffer_allocation_failed"); return; }
  canvas.fillScreen(BG);
  canvas.drawFastHLine(116,58,78,ACCENT);
  canvas.drawCircle(194,51,7,ACCENT);
  canvas.drawFastHLine(106,74,93,ACCENT);
  canvas.drawFastHLine(126,90,56,ACCENT);
  text(100,135,"Aervia",&FreeSansBold18pt7b);
  text(64,162,"Know the air you breathe",&FreeSans9pt7b,MUTED);
  canvas.drawRoundRect(60,187,200,6,3,CARD); showFrame();
  Serial.println("TFT_INTRO_START duration_ms=2500 rotation=3");
  uint32_t start=millis();
  for(int i=1;i<=50;++i) {
    canvas.fillRect(62,189,i*196/50,2,ACCENT);
    tft.fillRect(62,189,i*196/50,2,ACCENT);
    uint32_t target=start+i*50;
    while((int32_t)(millis()-target)<0) delay(1);
  }
  Serial.printf("TFT_INTRO_DONE elapsed_ms=%lu\n",(unsigned long)(millis()-start));
  renderPage("");
}
