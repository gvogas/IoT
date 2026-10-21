"""Receives sensor readings for the dashboard."""

import threading

import paho.mqtt.client as mqtt

from config import ALERT_RESET_MARGIN, FAN_COMMAND_TOPIC, MQTT_BROKER, MQTT_PORT
from controllers.fan_controller import fan_controller
from mail.send_email import send_temperature_alert
from models.fridge import Fridge


class MqttController:
    # Setup
    def __init__(self):
        self.fridges = [Fridge(1), Fridge(2)]
        self.readings = {}
        self.alert_sent = {}
        for fridge in self.fridges:
            self.readings[fridge.id] = {"temperature": None, "humidity": None}
            self.alert_sent[fridge.id] = False

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # Subcribe to sensor topic
    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"Connected with result code {reason_code}")
        for fridge in self.fridges:
            client.subscribe(fridge.temp_topic)
            client.subscribe(fridge.hum_topic)
        client.subscribe(FAN_COMMAND_TOPIC)

    #Receive senosr reading
    def on_message(self, client, userdata, msg):
        value = msg.payload.decode().strip()
        print(f"{msg.topic}: {value}")

        # Fan command, like "ON" after a YES reply to an alert email
        if msg.topic == FAN_COMMAND_TOPIC:
            if value.upper() == "ON":
                fan_controller.turn_on()
            elif value.upper() == "OFF":
                fan_controller.turn_off()
            print(f"Fan is {fan_controller.get_state()}")
            return

        for fridge in self.fridges:
            if msg.topic == fridge.temp_topic:
                self.readings[fridge.id]["temperature"] = value
                self.check_temperature(fridge, value)
            elif msg.topic == fridge.hum_topic:
                self.readings[fridge.id]["humidity"] = value

    # Email once when a fridge goes over its threshold.
    # Another email is only sent after it cools down again.
    def check_temperature(self, fridge, value):
        try:
            temperature = float(value)
        except ValueError:
            return

        threshold = fridge.get_threshold()
        if threshold is None:
            return

        if temperature > threshold and not self.alert_sent[fridge.id]:
            self.alert_sent[fridge.id] = True
            # Send in the background so MQTT keeps receiving while the email sends
            threading.Thread(
                target=send_temperature_alert,
                args=(fridge.id, temperature, threshold),
                daemon=True,
            ).start()
        elif temperature <= threshold - ALERT_RESET_MARGIN:
            self.alert_sent[fridge.id] = False

    #Start MQTT
    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    #Stop MQTT
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
