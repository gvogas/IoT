// All the ESP32 settings are here. If you need to change one, change it in this file.

// ---------- WiFi ----------

#define WIFI_SSID      "your-wifi"
#define WIFI_PASSWORD  "your-wifi-password"


// ---------- MQTT broker (same IP as MQTT_BROKER in config.py) ----------

#define MQTT_BROKER    "192.168.0.100"
#define MQTT_PORT      1883
#define MQTT_CLIENT    "ESP32-Fridges"
// The broker's username and password (the same as in the broker's password file).
// Delete these two lines if the broker doesn't ask for a password
#define MQTT_USER      "esp32"
#define MQTT_PASS      "your-mqtt-password"


// ---------- DHT11 sensor pins ----------

#define FRIDGE1_PIN    27
#define FRIDGE2_PIN    26
