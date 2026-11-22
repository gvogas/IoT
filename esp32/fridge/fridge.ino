/*********
https://www.electronicshub.org/esp32-dht11-tutorial/
  Rui Santos
  Complete project details at https://randomnerdtutorials.com
*********/

// One ESP32 per fridge. Set FRIDGE_NUMBER in config.h to 1 or 2 before uploading.

#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"
#include "DHT11Sensor.h"

// Don't change the topics: the Pi listens for "frig1/..." and "frig2/..."
#if FRIDGE_NUMBER == 1
DHT11Sensor fridge(SENSOR_PIN, "Fridge 1", "frig1/temperature", "frig1/humidity");
const char* clientName = "ESP32-Fridge1";
#else
DHT11Sensor fridge(SENSOR_PIN, "Fridge 2", "frig2/temperature", "frig2/humidity");
const char* clientName = "ESP32-Fridge2";
#endif

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.print("Connecting to Wifi:");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    bool ok;
    if (strlen(MQTT_USER) > 0) {
      ok = client.connect(clientName, MQTT_USER, MQTT_PASSWORD);   // the broker asks for a password
    } else {
      ok = client.connect(clientName);
    }

    if (ok) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  fridge.begin();

  setup_wifi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  fridge.readAndPublish(client);

  // "I'm alive" message. The app doesn't use it, but mosquitto_sub -t vanier shows the ESP32 is sending
  client.publish("vanier", clientName);
  delay(2000);
}
