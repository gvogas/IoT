# Pretends to be the ESP32 and the MSP01 Bluetooth sensor so you can test without the hardware.
# Run from the project folder: python3 -m tools.fake_sensors
# Set MQTT_BROKER = "localhost", FRIDGES_ENABLED = True and MSP01_ENABLED = True in config.py first.
import random
import time

import paho.mqtt.client as mqtt

from config import MQTT_BROKER, MQTT_PASSWORD, MQTT_PORT, MQTT_USERNAME, MSP01_TOPIC

# Seconds between readings
SEND_EVERY = 5

# The starting temperature of each fridge
temperatures = {1: 4.0, 2: 6.0}

# The starting temperature of the MSP01 (in Fridge 3)
msp01_temperature = 5.0

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if MQTT_USERNAME:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()
print(f"Sending fake readings to {MQTT_BROKER} every {SEND_EVERY} s. Ctrl+C to stop.")

try:
    while True:
        for fridge_id in temperatures:
            # Drift the temperature up or down a little, like a real fridge
            temperatures[fridge_id] += random.uniform(-0.5, 0.5)
            temperature = round(temperatures[fridge_id], 1)
            humidity = random.randint(40, 60)

            client.publish(f"frig{fridge_id}/temperature", temperature)
            client.publish(f"frig{fridge_id}/humidity", humidity)
            print(f"Frig{fridge_id}: {temperature} C, {humidity} %")

        # The MSP01 sensor, like "msp01/temperature" -> "5.2"
        msp01_temperature += random.uniform(-0.5, 0.5)
        temperature = round(msp01_temperature, 1)
        humidity = random.randint(40, 60)
        light = random.randint(0, 300)
        # Someone walks past about one time in five
        motion = 1 if random.random() < 0.2 else 0
        client.publish(f"{MSP01_TOPIC}/temperature", temperature)
        client.publish(f"{MSP01_TOPIC}/humidity", humidity)
        client.publish(f"{MSP01_TOPIC}/light", light)
        client.publish(f"{MSP01_TOPIC}/bright", 1 if light > 50 else 0)
        client.publish(f"{MSP01_TOPIC}/motion", motion)
        client.publish(f"{MSP01_TOPIC}/battery", 90)
        client.publish(f"{MSP01_TOPIC}/rssi", random.randint(-80, -50))
        print(f"MSP01: {temperature} C, {humidity} %, light {light}, motion {motion}")

        time.sleep(SEND_EVERY)
except KeyboardInterrupt:
    print("Stopped")
finally:
    client.loop_stop()
    client.disconnect()
