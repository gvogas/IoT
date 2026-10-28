"""Receives sensor readings for the dashboard."""

import sqlite3
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from config import ALERT_RESET_MARGIN, ALERT_TO, FAN_COMMAND_TOPIC, MQTT_BROKER, MQTT_PORT
from controllers.fan_controller import fan_controller
from mail.send_email import send_temperature_alert
from models.fridge import Fridge
from models.reading import save_reading, to_number

# How often to save a reading (seconds)
SAVE_EVERY = 60


class MqttController:
    # Setup
    def __init__(self):
        self.fridges = [Fridge(1), Fridge(2)]
        self.readings = {}
        self.alert_sent = {}
        self.alerts = {}
        self.last_saved = {}
        for fridge in self.fridges:
            self.readings[fridge.id] = {"temperature": None, "humidity": None, "updated": None}
            self.alert_sent[fridge.id] = False
            self.alerts[fridge.id] = None
            self.last_saved[fridge.id] = 0

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
                self.readings[fridge.id]["updated"] = time.time()
                self.check_temperature(fridge, value)
                self.save_if_due(fridge)
            elif msg.topic == fridge.hum_topic:
                self.readings[fridge.id]["humidity"] = value
                self.readings[fridge.id]["updated"] = time.time()

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
                target=self.send_alert,
                args=(fridge.id, temperature, threshold),
                daemon=True,
            ).start()
        elif temperature <= threshold - ALERT_RESET_MARGIN:
            self.alert_sent[fridge.id] = False
            self.alerts[fridge.id] = None

    # Save the reading to the database once a minute
    def save_if_due(self, fridge):
        now = time.time()
        if now - self.last_saved[fridge.id] < SAVE_EVERY:
            return
        data = self.readings[fridge.id]
        temperature = to_number(data["temperature"])
        if temperature is None:
            return
        try:
            save_reading(fridge.id, temperature, to_number(data["humidity"]))
            self.last_saved[fridge.id] = now
        except sqlite3.Error as err:
            # like "no such table: Reading" if init_database wasn't run again
            print(f"Could not save the reading for Frig{fridge.id}: {err}")

    # Send the email and save if it worked
    def send_alert(self, fridge_id, temperature, threshold):
        sent = send_temperature_alert(fridge_id, temperature, threshold)
        self.alerts[fridge_id] = {
            "status": "sent" if sent else "failed",
            "email": ALERT_TO,
            "time": datetime.now().strftime("%H:%M"),
        }

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
