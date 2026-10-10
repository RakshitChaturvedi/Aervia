#pragma once
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <LittleFS.h>
#include <esp_sntp.h>
#include <mbedtls/pk.h>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>
#include "GoogleRoots.h"

#include "ProjectConfig.h"
const char* FIELD_SHEET_ID=AERVIA_GOOGLE_SHEET_ID;
// Flat, typed raw observations. null becomes a blank cell, not numeric zero.
const char* FIELD_COLUMNS[]={
 "sequence","timestamp_ist","device_id","boot_id",
 "pm1_ug_m3","pm2_5_ug_m3","pm4_ug_m3","pm10_ug_m3",
 "nc0_5_per_cm3","nc1_0_per_cm3","nc2_5_per_cm3","nc4_per_cm3","nc10_per_cm3",
 "typical_particle_size_um","temp_c","humidity_rh_pct","pressure_hpa",
 "voc_index","nox_index","sraw_voc","sraw_nox","latitude","longitude",
 "battery_v","battery_pct","wifi_rssi_dbm","uptime_s","restart_count","boot_reason",
 "sps30_state","bme280_state","sgp41_state","sps30_status_raw","fan_fault","laser_fault",
 "fan_speed_warning","quality_flag","quality_flags","clock_source","clock_sync_age_s",
 "usb_packets_sent","usb_packets_dropped_local","packets_lost","queued_samples","uploaded_samples","storage_dropped_samples"};
const char* FIELD_KEYS[]={
 "sequence","timestamp","device_id","boot_id","pm1","pm2_5","pm4","pm10",
 "nc0_5","nc1_0","nc2_5","nc4","nc10","typical_particle_size","temp_c","humidity_rh",
 "pressure_hpa","voc_index","nox_index","sraw_voc","sraw_nox","latitude","longitude",
 "battery_v","battery_pct","wifi_rssi","uptime_s","restart_count","boot_reason",
 "sensor_status.sps30","sensor_status.bme280","sensor_status.sgp41","sps30_status_raw",
 "fan_fault","laser_fault","fan_speed_warning","quality_flag","quality_flags","timestamp_source",
 "clock_sync_age_s","packets_sent","packets_dropped_local","packets_lost",
 "queued_samples","uploaded_samples","storage_dropped_samples"};
constexpr size_t FIELD_COL_COUNT=sizeof(FIELD_COLUMNS)/sizeof(*FIELD_COLUMNS);
static_assert(FIELD_COL_COUNT==sizeof(FIELD_KEYS)/sizeof(*FIELD_KEYS));
String fieldSsid,fieldPassword,fieldEmail,fieldKey,fieldToken;
SemaphoreHandle_t fieldFsLock=nullptr;
bool fieldFsReady=false;
volatile bool fieldNtpEvent=false;
volatile int fieldWifiReason=0;
bool fieldScanPending=false;
time_t fieldTokenExpires=0;
String activeSegment;
uint32_t activeSegmentCount=0;
constexpr unsigned FIELD_BATCH=15;
constexpr size_t FIELD_STORAGE_LIMIT=1100000; // Bound existing 1.375 MiB data partition.

void fieldTimeSync(timeval*) {fieldNtpEvent=true;}
uint32_t fieldSessionNumber=0;
bool fieldPreparedOnly=false;
String fieldTab() {char title[32];snprintf(title,sizeof(title),"Session_%03lu",(unsigned long)fieldSessionNumber);return String(title);}
String encodeUrl(const String& s) {
 const char hex[]="0123456789ABCDEF";String result;
 for(size_t i=0;i<s.length();++i){unsigned char c=s[i];
  if(isalnum(c)||c=='-'||c=='_'||c=='.'||c=='~')result+=(char)c;
  else {result+='%';result+=hex[c>>4];result+=hex[c&15];}}
 return result;
}
String b64url(const uint8_t* bytes,size_t n) {
 size_t len=0;String result;
 size_t capacity=4*((n+2)/3)+1;
 auto buffer=std::unique_ptr<unsigned char[]>(new(std::nothrow) unsigned char[capacity]);
 if(!buffer || mbedtls_base64_encode(buffer.get(),capacity,&len,bytes,n))return result;
 for(size_t i=0;i<len;++i){char c=buffer[i];if(c=='=')break;result+=c=='+'?'-':c=='/'?'_':c;}
 return result;
}
int fieldRandom(void*,unsigned char* bytes,size_t size){esp_fill_random(bytes,size);return 0;}
String fieldJwt() {
 JsonDocument claims;time_t now=time(nullptr);
 claims["iss"]=fieldEmail;claims["scope"]="https://www.googleapis.com/auth/spreadsheets";
 claims["aud"]="https://oauth2.googleapis.com/token";claims["iat"]=(int64_t)now;claims["exp"]=(int64_t)now+3600;
 String payload;serializeJson(claims,payload);
 const char header[]="{\"alg\":\"RS256\",\"typ\":\"JWT\"}";
 String message=b64url((const uint8_t*)header,strlen(header))+"."+b64url((const uint8_t*)payload.c_str(),payload.length());
 mbedtls_pk_context key;mbedtls_pk_init(&key);
 int error=mbedtls_pk_parse_key(&key,(const unsigned char*)fieldKey.c_str(),fieldKey.length()+1,nullptr,0,fieldRandom,nullptr);
 unsigned char hash[32],signature[512];size_t size=0;
 if(!error && !mbedtls_pk_can_do(&key,MBEDTLS_PK_RSA))error=-1;
 if(!error)error=mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),(const unsigned char*)message.c_str(),message.length(),hash);
 if(!error)error=mbedtls_pk_sign(&key,MBEDTLS_MD_SHA256,hash,sizeof(hash),signature,sizeof(signature),&size,fieldRandom,nullptr);
 mbedtls_pk_free(&key);
 if(error){cloudState="Key signing failed";return "";}
 return message+"."+b64url(signature,size);
}
int fieldHttp(const String& url,const char* method,const String& body,String& response,bool auth=true) {
 WiFiClientSecure client;client.setCACert(GOOGLE_ROOTS);client.setHandshakeTimeout(12);
 HTTPClient http;http.setConnectTimeout(10000);http.setTimeout(15000);
 if(!http.begin(client,url))return -1;
 http.addHeader("Content-Type",auth?"application/json":"application/x-www-form-urlencoded");
 if(auth)http.addHeader("Authorization","Bearer "+fieldToken);
 int status=http.sendRequest(method,(uint8_t*)body.c_str(),body.length());
 if(status>0)response=http.getString();http.end();
 if(status==401){fieldToken="";fieldTokenExpires=0;}
 cloudHttpCode=status;return status;
}
bool fieldAuthenticate() {
 if(fieldToken.length() && time(nullptr)<fieldTokenExpires-120)return true;
 cloudState="Authenticating";
 String jwt=fieldJwt();if(!jwt.length())return false;
 String response;
 int code=fieldHttp("https://oauth2.googleapis.com/token","POST",
  "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion="+jwt,response,false);
 if(code!=200){cloudState="Google auth failed";return false;}
 JsonDocument d;if(deserializeJson(d,response)){cloudState="Auth response error";return false;}
 fieldToken=d["access_token"].as<String>();fieldTokenExpires=time(nullptr)+(d["expires_in"]|3600);
 return fieldToken.length()>0;
}
String fieldBase(){return String("https://sheets.googleapis.com/v4/spreadsheets/")+FIELD_SHEET_ID;}
bool fieldPut(const String& tab,uint32_t first,JsonArray rows,String& response) {
 if(!rows.size())return true;
 // Fixed row addresses make a replay after an ambiguous timeout idempotent.
 JsonDocument request;request["majorDimension"]="ROWS";request["values"].set(rows);
 String body;serializeJson(request,body);
 String range="'"+tab+"'!A"+String(first);
 int code=fieldHttp(fieldBase()+"/values/"+encodeUrl(range)+"?valueInputOption=RAW","PUT",body,response);
 if(code!=200){cloudState=code==403?"Share sheet / enable API":"Sheet write failed";return false;}
 JsonDocument result;if(deserializeJson(result,response))return false;
 return (result["updatedRows"]|0)==(int)rows.size();
}
String cachedTab;uint32_t cachedRows=0;
bool fieldEnsureTab(const String& title,uint32_t neededRows) {
 if(title==cachedTab && neededRows<=cachedRows)return true;
 String response;
 int code=fieldHttp(fieldBase()+"?fields=sheets.properties","GET","",response);
 if(code!=200){cloudState=code==403?"Share sheet / enable API":"Sheet access failed";return false;}
 JsonDocument metadata;if(deserializeJson(metadata,response))return false;
 int id=-1;uint32_t rows=0;
 for(JsonVariant sheet:metadata["sheets"].as<JsonArray>()) {
  if(sheet["properties"]["title"].as<String>()==title) {
   id=sheet["properties"]["sheetId"]|0;rows=sheet["properties"]["gridProperties"]["rowCount"]|0;break;}
 }
 uint32_t target=max((uint32_t)1000,((neededRows+999)/1000)*1000);
 if(id<0 || rows<neededRows) {
  JsonDocument change;JsonObject req=change["requests"].to<JsonArray>().add<JsonObject>();
  if(id<0) {
   JsonObject props=req["addSheet"]["properties"].to<JsonObject>();props["title"]=title;
   props["gridProperties"]["rowCount"]=target;props["gridProperties"]["columnCount"]=FIELD_COL_COUNT;
   props["gridProperties"]["frozenRowCount"]=1;
  }else {
   JsonObject add=req["appendDimension"].to<JsonObject>();add["sheetId"]=id;
   add["dimension"]="ROWS";add["length"]=target-rows;
  }
  String body;serializeJson(change,body);
  code=fieldHttp(fieldBase()+":batchUpdate","POST",body,response);
  if(code!=200){cloudState="Tab create/grow failed";return false;}
 }
 JsonDocument header;JsonArray all=header.to<JsonArray>();JsonArray row=all.add<JsonArray>();
 for(const char* column:FIELD_COLUMNS)row.add(column);
 bool ok=fieldPut(title,1,all,response);
 if(ok){cachedTab=title;cachedRows=(id<0 || rows<neededRows)?target:rows;}
 return ok;
}
void fieldCountQueue() {
 uint32_t count=0;File dir=LittleFS.open("/");File f=dir.openNextFile();
 while(f){if(String(f.name()).startsWith("q_")){while(f.available()){String line=f.readStringUntil('\n');if(line.startsWith("["))++count;}}f.close();f=dir.openNextFile();}
 cloudQueued=count;
}
void queueFieldRecord(JsonDocument& d) {
 if(fieldPreparedOnly)return;
 d["cloud_state"]=cloudState;d["cloud_http_code"]=cloudHttpCode;
 d["wifi_status"]=WiFi.status();d["wifi_disconnect_reason"]=fieldWifiReason;
 d["heap_free_bytes"]=ESP.getFreeHeap();
 d["queued_samples"]=cloudQueued;d["uploaded_samples"]=cloudUploaded;
 d["storage_dropped_samples"]=cloudDropped;
 if(!fieldFsReady){++cloudDropped;return;}
 JsonDocument record;JsonArray row=record.to<JsonArray>();
 for(const char* name:FIELD_KEYS) {
  if(!strcmp(name,"quality_flags")){String flags;serializeJson(d[name],flags);row.add(flags);}
  else if(!strncmp(name,"sensor_status.",14))row.add(d["sensor_status"][name+14]);
  else if(d[name].isNull())row.add("");else row.add(d[name]);
 }
 String encoded;serializeJson(record,encoded);
 if(xSemaphoreTake(fieldFsLock,pdMS_TO_TICKS(100))!=pdTRUE){++cloudDropped;return;}
 if(LittleFS.usedBytes()+encoded.length()+4096>FIELD_STORAGE_LIMIT){++cloudDropped;cloudState="Storage full: drops";xSemaphoreGive(fieldFsLock);return;}
 if(!activeSegment.length()) {
  char name[64];snprintf(name,sizeof(name),"/q_%08lu_%08lu.jsonl",(unsigned long)bootCount,(unsigned long)live.tick);
  activeSegment=name;activeSegmentCount=0;
 }
 bool fresh=!LittleFS.exists(activeSegment);File file=LittleFS.open(activeSegment,FILE_APPEND);
 bool ok=(bool)file;
 if(ok && fresh) {
  JsonDocument header;header["tab"]=fieldTab();header["first"]=live.tick;
  String encodedHeader;serializeJson(header,encodedHeader);encodedHeader+='\n';
  ok=file.print(encodedHeader)==encodedHeader.length();
 }
 if(ok){encoded+='\n';ok=file.print(encoded)==encoded.length();file.flush();}
 file.close();
 if(ok){++cloudQueued;++activeSegmentCount;if(activeSegmentCount>=FIELD_BATCH){activeSegment="";activeSegmentCount=0;}}
 else {++cloudDropped;cloudState="Flash write failed";activeSegment="";activeSegmentCount=0;}
 xSemaphoreGive(fieldFsLock);
}
String fieldOldestSegment() {
 String result;File dir=LittleFS.open("/");File f=dir.openNextFile();
 while(f){String path="/"+String(f.name());if(path.startsWith("/q_") && path!=activeSegment && (!result.length() || path<result))result=path;
  f.close();f=dir.openNextFile();}
 return result;
}
bool fieldUploadSegment() {
 JsonDocument metadata,values;JsonArray rows=values.to<JsonArray>();String path;
 xSemaphoreTake(fieldFsLock,portMAX_DELAY);path=fieldOldestSegment();
 if(!path.length()){xSemaphoreGive(fieldFsLock);return true;}
 // Read the whole small segment in one filesystem call, then parse without
 // holding the writer lock. Byte-at-a-time Stream reads held it too long.
 File file=LittleFS.open(path);bool valid=(bool)file;String content;
 if(valid) {
  size_t n=file.size();valid=n>0 && n<=32768 && content.reserve(n+1);
  if(valid){auto bytes=std::unique_ptr<char[]>(new(std::nothrow) char[n+1]);
   valid=(bool)bytes;
   if(valid){valid=file.readBytes(bytes.get(),n)==n;bytes[n]=0;if(valid)content=bytes.get();}}
 }
 file.close();xSemaphoreGive(fieldFsLock);
 int cursor=content.indexOf('\n');
 if(valid)valid=cursor>=0 && !deserializeJson(metadata,content.substring(0,cursor));
 ++cursor;
 while(valid && cursor<(int)content.length()) {
  int end=content.indexOf('\n',cursor);if(end<0)end=content.length();
  String line=content.substring(cursor,end);cursor=end+1;if(!line.length())continue;
  JsonDocument record;valid=!deserializeJson(record,line) && record.is<JsonArray>() && record.size()==FIELD_COL_COUNT;
  if(valid)rows.add(record.as<JsonArray>());
 }
 if(!valid || !rows.size()){cloudState="Stored segment error";return false;}
 String tab=metadata["tab"].as<String>();uint32_t first=metadata["first"]|0;
 if(!first || !tab.startsWith("Session_")){cloudState="Stored metadata error";return false;}
 if(!fieldEnsureTab(tab,first+rows.size()+1))return false;
 String response;cloudState="Uploading";
 if(!fieldPut(tab,first+1,rows,response))return false;
 xSemaphoreTake(fieldFsLock,portMAX_DELAY);
 bool removed=LittleFS.remove(path);if(removed){cloudQueued-=min((uint32_t)cloudQueued,(uint32_t)rows.size());cloudUploaded+=rows.size();}
 xSemaphoreGive(fieldFsLock);
 cloudState=removed?"Sheets logging":"Queue remove failed";
 return removed;
}
void fieldWorker(void*) {
 uint32_t retryMs=2000,lastReconnect=millis();bool startedTab=false;
 while(true) {
  if(!fieldSsid.length()){cloudState="Wi-Fi setup needed";vTaskDelay(pdMS_TO_TICKS(1000));continue;}
  if(WiFi.status()!=WL_CONNECTED){cloudState="Connecting Wi-Fi";if(millis()-lastReconnect>30000){WiFi.reconnect();lastReconnect=millis();}vTaskDelay(pdMS_TO_TICKS(1000));continue;}
  if(!clockSynced){cloudState="Waiting for NTP";vTaskDelay(pdMS_TO_TICKS(1000));continue;}
  if(!fieldEmail.length() || !fieldKey.length()){cloudState="Google key needed";vTaskDelay(pdMS_TO_TICKS(1000));continue;}
  if(!fieldFsReady){cloudState="Storage setup needed";vTaskDelay(pdMS_TO_TICKS(1000));continue;}
  if(!strlen(FIELD_SHEET_ID)){cloudState="Set Google Sheet ID";vTaskDelay(pdMS_TO_TICKS(1000));continue;}
  bool ok=fieldAuthenticate();
  if(ok && !startedTab){ok=fieldEnsureTab(fieldTab(),1000);startedTab=ok;}
  if(ok)ok=fieldUploadSegment();
  if(ok){retryMs=2000;if(cloudQueued==0)cloudState="Sheets logging";}
  vTaskDelay(pdMS_TO_TICKS(ok?2000:retryMs+(esp_random()%1000)));
  if(!ok)retryMs=min(retryMs*2,(uint32_t)60000);
 }
}
bool handleFieldCommand(const char* command) {
 if(!strcmp(command,"NET")) {
  Serial.printf("WIFI_DIAG ssid=%s configured=%u google_key=%u status=%d reason=%d free_heap=%lu\n",
   fieldSsid.c_str(),fieldSsid.length()>0,fieldKey.length()>0,(int)WiFi.status(),fieldWifiReason,(unsigned long)ESP.getFreeHeap());
  if(WiFi.scanComplete()!=WIFI_SCAN_RUNNING){WiFi.scanNetworks(true);fieldScanPending=true;}
  return true;
 }
 if(!strcmp(command,"FORMAT")) {
  if(fieldFsReady){Serial.println("STORAGE_ALREADY_READY no_format_performed");return true;}
  if(LittleFS.format() && LittleFS.begin(false)){fieldFsReady=true;Serial.println("STORAGE_READY");}
  else Serial.println("STORAGE_INIT_FAILED");
  return true;
 }
 if(strncmp(command,"CONFIG ",7))return false;
 JsonDocument cfg;if(deserializeJson(cfg,command+7)){Serial.println("CONFIG_ERROR invalid_json");return true;}
 String email=cfg["client_email"]|"",key=cfg["private_key"]|"";
 if((email.length() && !email.endsWith(".iam.gserviceaccount.com")) ||
    (key.length() && !key.startsWith("-----BEGIN PRIVATE KEY-----"))) {Serial.println("CONFIG_ERROR invalid_service_account");return true;}
 Preferences p;if(!p.begin("vbfield",false)){Serial.println("CONFIG_ERROR storage");return true;}
 bool ok=true;
 for(const char* name:{"ssid","password","client_email","private_key"}) {
  if(cfg[name].is<String>()) {
   const char* n=!strcmp(name,"client_email")?"email":!strcmp(name,"private_key")?"key":name;
   String v=cfg[name].as<String>();ok &= p.putString(n,v)==v.length();
  }
 }
 p.end();Serial.setTxTimeoutMs(200);Serial.println(ok?"CONFIG_SAVED restarting":"CONFIG_ERROR save_failed");
 if(ok){Serial.flush();delay(300);ESP.restart();}Serial.setTxTimeoutMs(0);return true;
}
void fieldBegin() {
 fieldFsLock=xSemaphoreCreateMutex();
 if(!fieldFsLock){cloudState="Queue lock failed";return;}
 fieldFsReady=LittleFS.begin(false);
 // One-time transition: discard the explicitly cancelled bench backlog, then
 // remain idle until the next power-up so the field session starts at 001.
 Preferences naming;
 if(!naming.begin("vbfield",false)){cloudState="Session storage failed";fieldPreparedOnly=true;return;}
 if(!naming.getBool("naming_v1",false) || !naming.getBool("ist_v1",false)) {
  if(!fieldFsReady){naming.end();cloudState="Queue cleanup failed";fieldPreparedOnly=true;return;}
  File dir=LittleFS.open("/");File f=dir.openNextFile();
  bool cleared=true;
  while(f){String name=f.name();f.close();if(name.startsWith("q_"))cleared &= LittleFS.remove("/"+name);f=dir.openNextFile();}
  dir.close();
  if(cleared){naming.putUInt("session",0);naming.putBool("naming_v1",true);naming.putBool("ist_v1",true);}
  naming.end();fieldPreparedOnly=true;cloudState=cleared?"Ready: power cycle":"Queue cleanup failed";
  Serial.println(cleared?"FIELD_READY next_session=Session_001 backlog_cleared":"FIELD_PREPARE_FAILED");return;
 }
 fieldSessionNumber=naming.getUInt("session",0)+1;
 if(naming.putUInt("session",fieldSessionNumber)!=sizeof(uint32_t)){naming.end();fieldPreparedOnly=true;cloudState="Session save failed";return;}
 naming.end();
 if(fieldFsReady)fieldCountQueue();
 Preferences p;if(p.begin("vbfield",true)){
  fieldSsid=p.getString("ssid","");fieldPassword=p.getString("password","");
  fieldEmail=p.getString("email","");fieldKey=p.getString("key","");p.end();}
 WiFi.onEvent([](arduino_event_id_t event,arduino_event_info_t info){
  if(event==ARDUINO_EVENT_WIFI_STA_DISCONNECTED)fieldWifiReason=info.wifi_sta_disconnected.reason;
 });
 if(fieldSsid.length()){WiFi.mode(WIFI_STA);WiFi.setSleep(false);WiFi.setAutoReconnect(true);WiFi.begin(fieldSsid.c_str(),fieldPassword.c_str());}
 sntp_set_time_sync_notification_cb(fieldTimeSync);
 configTime(0,0,"time.google.com","pool.ntp.org","time.cloudflare.com");
 if(xTaskCreatePinnedToCore(fieldWorker,"sheets",12288,nullptr,1,nullptr,0)!=pdPASS)cloudState="Upload task failed";
}
void fieldLoop() {
 if(fieldScanPending && WiFi.scanComplete()!=WIFI_SCAN_RUNNING) {
  int count=WiFi.scanComplete();bool found=false;
  for(int i=0;i<count;++i)if(WiFi.SSID(i)==fieldSsid){found=true;Serial.printf("WIFI_TARGET_FOUND channel=%d rssi=%d security=%d\n",WiFi.channel(i),WiFi.RSSI(i),(int)WiFi.encryptionType(i));}
  Serial.printf("WIFI_TARGET_VISIBLE=%u scan_result=%d\n",found,count);WiFi.scanDelete();fieldScanPending=false;
 }
 if(fieldNtpEvent){fieldNtpEvent=false;clockSynced=true;clockSyncAt=esp_timer_get_time();clockSource="ntp";}
}
