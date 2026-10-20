// One DHT11 sensor for one fridge. It reads the sensor, prints the numbers and sends them to MQTT
#pragma once

#include <PubSubClient.h>
#include "DHT.h"

class DHT11Sensor {
  public:

    DHT11Sensor(int pin, const char* name, const char* tempTopic, const char* humTopic)
      : dht(pin, DHT11), name(name), tempTopic(tempTopic), humTopic(humTopic) {}

    // Call once in setup()
    void begin() {
      dht.begin();
    }


    void readAndPublish(PubSubClient &client) {
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();

      if (isnan(temperature) || isnan(humidity)) {
        Serial.print(name);
        Serial.println(": failed to read from DHT sensor");
        return;
      }

      // Print the readings to the Serial Monitor
      Serial.println(name);

      Serial.print("Temperature: ");
      Serial.print(temperature);
      Serial.println(" °C");

      Serial.print("Humidity: ");
      Serial.print(humidity);
      Serial.println(" %");
      Serial.println("-------------------------");


      // Convert the numbers to text for MQTT.
      char tempString[8];
      char humString[8];

      dtostrf(temperature, 6, 2, tempString);
      dtostrf(humidity, 6, 2, humString);

      client.publish(tempTopic, tempString);
      client.publish(humTopic, humString);
    }

  private:
    DHT dht;
    const char* name;
    const char* tempTopic;
    const char* humTopic;
};
