// All the ESP32 settings are here. If you need to change one, change it in this file.
// There is one ESP32 per fridge. Both run this same code, only FRIDGE_NUMBER (and the login) changes.

// -------------------------
// Which fridge this ESP32 is in (1 or 2)
// -------------------------

#define FRIDGE_NUMBER  1

// -------------------------
// WiFi
// -------------------------

#define WIFI_SSID      "your-wifi"
#define WIFI_PASSWORD  "your-password"

// -------------------------
// MQTT broker (the Raspberry Pi). Use the same IP as MQTT_BROKER in config.py on the Pi
// -------------------------

#define MQTT_BROKER    "192.168.0.100"

#define MQTT_PORT      1883

// This ESP32's broker login (the same as in the broker's password file). Each ESP32 can have its own
// Leave MQTT_USER empty if the broker has no passwords yet
#define MQTT_USER      ""
#define MQTT_PASSWORD  "your-password"

// -------------------------
// DHT11 sensor pin
// -------------------------

#define SENSOR_PIN     27
