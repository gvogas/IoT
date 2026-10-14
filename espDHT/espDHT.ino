/*********
https://www.electronicshub.org/esp32-dht11-tutorial/
  Rui Santos
  Complete project details at https://randomnerdtutorials.com  
*********/

//#include <WiFi.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"

// DHT11 sensor pin
#define DHT11PIN1 27 //frige 1
#define DHT11PIN2 26 //firige 2


DHT dht1(DHT11PIN1, DHT11);
DHT dht2(DHT11PIN2, DHT11);


//*School wifi
// const char* ssid = "iotvanier";
// const char* password = "14730078";

//*home wifi
const char* ssid = "iotvanier";
const char* password = "14730078";

//*school MQTT broker
const char* mqtt_server = "192.168.50.107";
const int mqtt_port = 1883;

//*Home MQTT broker
// const char* mqtt_server = "192.168.50.107";

const char* frig1 = "frig1/temperature";
const char* frig1h = "frig1/humidity";
const char* frig2 = "frig2/temperature";
const char* frig2h = "frig2/humidity";

WiFiClient espClient;
PubSubClient client(espClient);


void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.print("Connecting to Wifi:");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}


void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP32-Fridges")) {
      Serial.println("connected");
     
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

// Read sensor data and publish to MQTT
void readAndPubData(DHT &sensor, const char* tempTopic, const char* humTopic, const char* sensorName) {
  float temperature = sensor.readTemperature();
  float humidity = sensor.readHumidity();

  // DHT11 fails to read; skip publishing bad values
  if (isnan(temperature) || isnan(humidity)) {
    Serial.print(sensorName);
    Serial.println(": failed to read from DHT sensor");
    return;
  }

  // Convert readings to strings
  char tempString[8];
  char humString[8];

  dtostrf(temperature, 6, 2, tempString);
  dtostrf(humidity, 6, 2, humString);

  // Display readings
  Serial.println("-------------------------");
  Serial.println(sensorName);

  Serial.print("Temperature: ");
  Serial.print(tempString);
  Serial.println(" °C");

  Serial.print("Humidity: ");
  Serial.print(humString);
  Serial.println(" %");

  // Publish readings to MQTT
  client.publish(tempTopic, tempString);
  client.publish(humTopic, humString);
}


void setup() {
  Serial.begin(115200);
  dht1.begin();
  dht2.begin();

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  //firge1
  readAndPubData(dht1,frig1,frig1h,"Fridge 1");

  //frigde 2
   readAndPubData(dht2,frig2,frig2h,"Fridge 2");

  
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