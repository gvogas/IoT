/*********
https://www.electronicshub.org/esp32-dht11-tutorial/
  Rui Santos
  Complete project details at https://randomnerdtutorials.com  
*********/

#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"
#include "DHT11Sensor.h"

// Don't change the topics: the Pi listens for "frig1/..." and "frig2/..."
DHT11Sensor fridge1(FRIDGE1_PIN, "Fridge 1", "frig1/temperature", "frig1/humidity");
DHT11Sensor fridge2(FRIDGE2_PIN, "Fridge 2", "frig2/temperature", "frig2/humidity");

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
    if (client.connect(MQTT_CLIENT)) {
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
  fridge1.begin();
  fridge2.begin();

  setup_wifi();
  client.setServer(MQTT_BROKER, MQTT_PORT);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  fridge1.readAndPublish(client);
  fridge2.readAndPublish(client);

  // "I'm alive" message. The app doesn't use it, but mosquitto_sub -t vanier shows the ESP32 is sending
  client.publish("vanier", "I am ESP32");
  delay(2000);
}
