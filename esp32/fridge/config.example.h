// All the ESP32 settings are here. If you need to change one, change it in this file.

// -------------------------
// WiFi
// -------------------------

#define WIFI_SSID      "your-wifi"
#define WIFI_PASSWORD  "your-wifi-password"


// -------------------------
// MQTT broker (the Raspberry Pi). Use the same IP as MQTT_BROKER in config.py on the Pi
// -------------------------

#define MQTT_BROKER    "192.168.0.100"
#define MQTT_PORT      1883
#define MQTT_CLIENT    "ESP32-Fridges"


// -------------------------
// DHT11 sensor pins
// -------------------------

#define FRIDGE1_PIN    27
#define FRIDGE2_PIN    26
