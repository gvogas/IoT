// One DHT11 sensor for one fridge. It reads the sensor, prints the numbers and sends them to MQTT
#pragma once

#include <PubSubClient.h>
#include "DHT.h"

class DHT11Sensor {
  public:
    // pin: the ESP32 pin that the sensor's data wire goes to
    // name: what the Serial Monitor shows, like "Fridge 1"
    // tempTopic / humTopic: where to send the readings, like "frig1/temperature" and "frig1/humidity"
    DHT11Sensor(int pin, const char* name, const char* tempTopic, const char* humTopic)
      : dht(pin, DHT11), name(name), tempTopic(tempTopic), humTopic(humTopic) {}

    // Call once in setup()
    void begin() {
      dht.begin();
    }

    // Read the sensor. Gives back false if the DHT11 did not work this time
    bool read() {
      temperature = dht.readTemperature();
      humidity = dht.readHumidity();

      if (isnan(temperature) || isnan(humidity)) {
        Serial.print(name);
        Serial.println(": failed to read from DHT sensor");
        return false;
      }
      return true;
    }

    // Show the newest reading in the Serial Monitor
    void print() {
      Serial.println("-------------------------");
      Serial.println(name);

      Serial.print("Temperature: ");
      Serial.print(temperature);
      Serial.println(" °C");

      Serial.print("Humidity: ");
      Serial.print(humidity);
      Serial.println(" %");
    }

    // Send the newest reading to the MQTT broker
    void publish(PubSubClient &client) {
      char tempString[8];
      char humString[8];

      dtostrf(temperature, 6, 2, tempString);
      dtostrf(humidity, 6, 2, humString);

      client.publish(tempTopic, tempString);
      client.publish(humTopic, humString);
    }

    // Read, print and send, all in one. If the reading did not work, it skips it
    void readAndPublish(PubSubClient &client) {
      if (read()) {
        print();
        publish(client);
      }
    }

  private:
    DHT dht;
    const char* name;
    const char* tempTopic;
    const char* humTopic;
    float temperature = NAN;
    float humidity = NAN;
};
