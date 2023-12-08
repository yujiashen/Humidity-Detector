#include "secrets.h"
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include "WiFi.h"
#include "time.h"

#include "DHT.h"
#define DHTPIN 19
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define AWS_IOT_PUBLISH_TOPIC   "esp32/pub"
#define AWS_IOT_SUBSCRIBE_TOPIC "esp32/sub"
WiFiClientSecure net = WiFiClientSecure();
MQTTClient client = MQTTClient(256);
unsigned long lastPublishTime = 0;

void connectAWS()
{
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.println("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED){
    delay(500);
    Serial.print(".");
  }

  Serial.println("Connected to Wi-Fi");

  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  client.begin(AWS_IOT_ENDPOINT, 8883, net);

  client.onMessage(messageHandler);

  Serial.print("Connecting to AWS IOT");

  while (!client.connect(THINGNAME)) {
    Serial.print(".");
    delay(100);
  }

  if(!client.connected()){
    Serial.println("AWS IoT Timeout!");
    return;
  }

  // Subscribe to a topic
  client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC);
  Serial.println("AWS IoT Connected!");
}

void publishMessage()
{
  float h = dht.readHumidity();
  float f = dht.readTemperature(true);
  struct tm timeinfo;
  if(!getLocalTime(&timeinfo)){
    Serial.println("Failed to obtain time");
    return;
  }
  char timestamp[20];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", &timeinfo);
  StaticJsonDocument<200> doc;
  doc["device_id"] = THINGNAME;
  doc["time"] = timestamp;
  doc["temperature"] = f;
  doc["humidity"] = h;
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer); // print to client
  Serial.println(jsonBuffer);
  client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
  Serial.println("Sent a message");
}

void messageHandler(String &topic, String &payload) {
  Serial.println("incoming: " + topic + " - " + payload);
  publishMessage();
}

void setup() {
  Serial.begin(9600);
  dht.begin();
  connectAWS();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void loop() {
  client.loop();
  unsigned long currentTime = millis();
  if (currentTime - lastPublishTime >= 3600000) {
    publishMessage();
    lastPublishTime = currentTime;
  }
}