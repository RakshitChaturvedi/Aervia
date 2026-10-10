#pragma once
#include <MQTT.h>
#include <WiFiClientSecure.h>
#include "AwsRoot.h"

const char* AWS_THING="Aervia_sensors";
const char* AWS_TOPIC="aervia/Aervia_sensors/telemetry";
String awsEndpoint,awsCertificate,awsPrivateKey;
QueueHandle_t awsQueue=nullptr;
bool awsConfigured=false;
volatile bool awsPending=false;
struct AwsMessage {char* payload;size_t length;};
constexpr unsigned AWS_QUEUE_CAPACITY=60;
// Only this worker touches the TLS and MQTT clients; sensing never waits for MQTT.
void awsWorker(void*) {
 WiFiClientSecure tls;MQTTClient mqtt(256,256);
 tls.setCACert(AWS_ROOT_CA);tls.setCertificate(awsCertificate.c_str());tls.setPrivateKey(awsPrivateKey.c_str());
 tls.setHandshakeTimeout(12);tls.setTimeout(10000);
 mqtt.begin(awsEndpoint.c_str(),8883,tls);mqtt.setOptions(30,true,10000);
 AwsMessage pending={nullptr,0};uint32_t backoff=2000;
 while(true) {
  if(WiFi.status()!=WL_CONNECTED || !clockSynced) {
   awsConnected=false;awsState=WiFi.status()!=WL_CONNECTED?"Waiting for Wi-Fi":"Waiting for NTP";
   if(mqtt.connected())mqtt.disconnect();
   vTaskDelay(pdMS_TO_TICKS(500));continue;
  }
  if(!mqtt.connected()) {
   awsConnected=false;awsState="Connecting AWS";
   if(!mqtt.connect(AWS_THING)) {
    awsError=(int)mqtt.lastError();awsConnack=(int)mqtt.returnCode();awsState="AWS connect failed";tls.stop();
    vTaskDelay(pdMS_TO_TICKS(backoff+(esp_random()%500)));backoff=min(backoff*2,(uint32_t)60000);continue;
   }
   awsConnected=true;awsError=0;awsConnack=0;backoff=2000;awsState="AWS connected";
  }
  if(!mqtt.loop()){awsConnected=false;awsError=(int)mqtt.lastError();awsState="AWS disconnected";tls.stop();continue;}
  if(!pending.payload){xQueueReceive(awsQueue,&pending,pdMS_TO_TICKS(20));awsPending=pending.payload!=nullptr;}
  if(pending.payload) {
   // QoS 1 publish returns only after PUBACK. Retry the same observation on failure.
   // Consumers deduplicate with (device_id, boot_id, sequence).
   if(mqtt.publish(AWS_TOPIC,pending.payload,(int)pending.length,false,1)) {
    ++awsAcknowledged;free(pending.payload);pending={nullptr,0};awsPending=false;awsState="AWS publishing";awsError=0;
   }else {awsError=(int)mqtt.lastError();awsState="AWS publish retry";mqtt.disconnect();tls.stop();awsConnected=false;}
  }
  awsQueued=uxQueueMessagesWaiting(awsQueue)+(pending.payload?1:0);
  vTaskDelay(pdMS_TO_TICKS(10));
 }
}
void queueAwsRecord(JsonDocument& d) {
 d["aws_configured"]=awsConfigured;d["aws_connected"]=(bool)awsConnected;
 d["aws_state"]=awsState;d["aws_acknowledged_samples"]=(uint32_t)awsAcknowledged;
 d["aws_queued_samples"]=(uint32_t)awsQueued;d["aws_dropped_local"]=(uint32_t)awsDropped;
 d["aws_last_error"]=(int)awsError;d["aws_connack"]=(int)awsConnack;
 if(!awsConfigured || !awsQueue)return;
 size_t size=measureJson(d);
 char* payload=(char*)heap_caps_malloc(size+1,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
 if(!payload){++awsDropped;return;}
 serializeJson(d,payload,size+1);AwsMessage message={payload,size};
 if(xQueueSend(awsQueue,&message,0)!=pdPASS){free(payload);++awsDropped;}
 awsQueued=uxQueueMessagesWaiting(awsQueue)+(awsPending?1:0);
}
bool handleAwsCommand(const char* command) {
 if(strncmp(command,"AWS ",4))return false;
 JsonDocument cfg;if(deserializeJson(cfg,command+4)){Serial.println("AWS_CONFIG_ERROR invalid_json");return true;}
 Preferences p;if(!p.begin("aerviaaws",false)){Serial.println("AWS_CONFIG_ERROR storage");return true;}
 String endpoint=cfg["endpoint"].is<String>()?cfg["endpoint"].as<String>():p.getString("endpoint","");
 String cert=cfg["certificate"].is<String>()?cfg["certificate"].as<String>():p.getString("cert","");
 String key=cfg["private_key"].is<String>()?cfg["private_key"].as<String>():p.getString("key","");
 bool hostOK=endpoint.isEmpty() || endpoint.endsWith("-ats.iot.ap-south-1.amazonaws.com");
 for(char c:endpoint)if(!(isalnum(c)||c=='-'||c=='.'))hostOK=false;
 if(!hostOK || !cert.startsWith("-----BEGIN CERTIFICATE-----") ||
    !(key.startsWith("-----BEGIN PRIVATE KEY-----")||key.startsWith("-----BEGIN RSA PRIVATE KEY-----"))) {
  p.end();Serial.println("AWS_CONFIG_ERROR invalid_endpoint_or_pem");return true;
 }
 // Mark incomplete until every value is committed; staged credentials can await an endpoint.
 p.putBool("ready",false);
 bool ok=p.putString("cert",cert)==cert.length();ok &= p.putString("key",key)==key.length();
 if(endpoint.length())ok &= p.putString("endpoint",endpoint)==endpoint.length();
 if(ok && endpoint.length())ok=p.putBool("ready",true)>0;p.end();
 if(ok && !endpoint.length()){awsState="Waiting for endpoint";Serial.println("AWS_CONFIG_SAVED waiting_endpoint");return true;}
 Serial.setTxTimeoutMs(200);Serial.println(ok?"AWS_CONFIG_SAVED restarting":"AWS_CONFIG_ERROR save_failed");
 if(ok){Serial.flush();delay(300);ESP.restart();}Serial.setTxTimeoutMs(0);return true;
}
void awsBegin() {
 Preferences p;if(p.begin("aerviaaws",true)){
  awsEndpoint=p.getString("endpoint","");awsCertificate=p.getString("cert","");awsPrivateKey=p.getString("key","");
  if(!p.getBool("ready",false))awsEndpoint="";p.end();}
 awsConfigured=awsEndpoint.length() && awsCertificate.length() && awsPrivateKey.length();
 if(!awsConfigured){awsState=awsCertificate.length() && awsPrivateKey.length()?"Waiting for endpoint":"AWS setup needed";return;}
 awsQueue=xQueueCreate(AWS_QUEUE_CAPACITY,sizeof(AwsMessage));
 if(!awsQueue){awsConfigured=false;awsState="AWS queue failed";return;}
 if(xTaskCreatePinnedToCore(awsWorker,"aws",8192,nullptr,1,nullptr,0)!=pdPASS){vQueueDelete(awsQueue);awsQueue=nullptr;awsConfigured=false;awsState="AWS task failed";}
}
