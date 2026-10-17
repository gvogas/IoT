import sqlite3
import paho.mqtt.client as mqtt

from config import DB_PATH, MQTT_BROKER, MQTT_PORT, FAN_PINS
from hardware.fan import Fan
from models.fridge import Fridge

# app.py starts this with mqtt_server.start(). It runs in the background while the website runs
# (you can also run it by itself with: python mqtt_server.py)

# The fan, connected to the Pi through the motor driver
fan = Fan(*FAN_PINS)

# Fridge 2 has no fan wired yet
fridges = [
    Fridge(1, fan),
    Fridge(2),
]

# The newest readings, for the dashboard. Like readings[1]["temperature"]
readings = {}
for fridge in fridges:
    readings[fridge.id] = {"temperature": None, "humidity": None, "fan": "OFF"}


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")

    for fridge in fridges:
        client.subscribe(fridge.temp_topic)
        client.subscribe(fridge.hum_topic)
        client.subscribe(fridge.fan_topic)

# This runs every time a new message comes in from the broker
def on_message(client, userdata, msg):
    value = msg.payload.decode().strip()
    print(msg.topic+": "+value)

    for fridge in fridges:
        # Save the newest value for the dashboard
        if msg.topic == fridge.temp_topic:
            readings[fridge.id]["temperature"] = value
        elif msg.topic == fridge.hum_topic:
            readings[fridge.id]["humidity"] = value
        elif msg.topic == fridge.fan_topic:
            readings[fridge.id]["fan"] = value

        # Turn this fridge's fan on if its temperature is higher than the threshold
        if msg.topic != fridge.temp_topic:
            continue
        try:
            state = fridge.check_temperature(float(value))
        except ValueError:
            print(f"  not a number: {value}")
            return
        except sqlite3.Error as err:
            print(f"  database error: {err}")
            return
        if state is None:
            print(f"  no threshold for fridge {fridge.id} in {DB_PATH}")
            return

        # Send the fan state so the dashboard can show it
        client.publish(fridge.fan_topic, state, retain=True)
        print(f"  threshold {fridge.get_threshold()} -> {fridge.fan_topic} {state}")

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message


# Connect to the broker and start listening in the background. app.py calls this
def start():
    print("Using database:", DB_PATH)
    # The broker IP (school or home) is in config.py
    mqttc.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqttc.loop_start()


# Stop listening and turn the fan off. app.py calls this when it closes
def stop():
    mqttc.loop_stop()
    fan.off()


# This part only runs when you run this file by itself, not when app.py uses it
if __name__ == "__main__":
    print("Using database:", DB_PATH)
    mqttc.connect(MQTT_BROKER, MQTT_PORT, 60)
    try:
        mqttc.loop_forever()
    finally:
        fan.cleanup()
