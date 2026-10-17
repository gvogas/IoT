/*********
https://www.electronicshub.org/esp32-dht11-tutorial/
  Rui Santos
  Complete project details at https://randomnerdtutorials.com  
*********/

//#include <WiFi.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"        // WiFi, broker and pin settings
#include "DHT11Sensor.h"

// The two DHT11 sensors on this ESP32: pin, name, temperature topic, humidity topic
// (don't change the topics, the Pi listens for "frig1/..." and "frig2/...")
DHT11Sensor fridge1(FRIDGE1_PIN, "Fridge 1", "frig1/temperature", "frig1/humidity");
DHT11Sensor fridge2(FRIDGE2_PIN, "Fridge 2", "frig2/temperature", "frig2/humidity");

WiFiClient espClient;
PubSubClient client(espClient);


void setup_wifi() {
  delay(10);
  // First, connect to the WiFi
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
  // Keep trying until we are connected again
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Try to connect
    if (client.connect(MQTT_CLIENT)) {
      Serial.println("connected");
     
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds, then try again
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

  client.publish("vanier", "I am ESP32");
  delay(2000);
}




// void callback(char* topic, byte* message, unsigned int length) {
//   Serial.print("Message arrived on topic: ");
//   Serial.print(topic);
//   Serial.print(". Message: ");
//   String messageTemp;
  
//   for (int i = 0; i < length; i++) {
//     Serial.print((char)message[i]);
//     messageTemp += (char)message[i];
//   }
//   Serial.println();

// Feel free to add more if statements to control more GPIOs with MQTT

// If a message is received on the topic esp32/output, you check if the message is either "on" or "off". 
// Changes the output state according to the message
//   if (String(topic) == "esp32/output") {
//     Serial.print("Changing output to ");
//     if(messageTemp == "on"){
//       Serial.println("on");
//       digitalWrite(ledPin, HIGH);
//     }
//     else if(messageTemp == "off"){
//       Serial.println("off"); 
//       digitalWrite(ledPin, LOW);
//     }
//   }
// }