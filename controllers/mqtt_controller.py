"""Receives sensor readings for the dashboard."""

import paho.mqtt.client as mqtt

from config import MQTT_BROKER, MQTT_PORT
from models.fridge import Fridge


class MqttController:
    def __init__(self):
        self.fridges = [Fridge(1), Fridge(2)]
        self.readings = {}
        for fridge in self.fridges:
            self.readings[fridge.id] = {"temperature": None, "humidity": None}

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"Connected with result code {reason_code}")
        for fridge in self.fridges:
            client.subscribe(fridge.temp_topic)
            client.subscribe(fridge.hum_topic)

    def on_message(self, client, userdata, msg):
        value = msg.payload.decode().strip()
        print(f"{msg.topic}: {value}")
        for fridge in self.fridges:
            if msg.topic == fridge.temp_topic:
                self.readings[fridge.id]["temperature"] = value
            elif msg.topic == fridge.hum_topic:
                self.readings[fridge.id]["humidity"] = value

    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


# Flask routes and app.py use the same readings and MQTT connection.
mqtt_controller = MqttController()


# Run from the project folder: python -m controllers.mqtt_controller
if __name__ == "__main__":
    mqtt_controller.client.connect(MQTT_BROKER, MQTT_PORT, 60)
    try:
        mqtt_controller.client.loop_forever()
    finally:
        mqtt_controller.client.disconnect()
