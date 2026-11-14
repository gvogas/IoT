"""Receives sensor readings for the dashboard."""

import logging
import sqlite3
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from config import (ALERT_RESET_MARGIN, ALERT_TO, MQTT_BROKER, MQTT_PASSWORD, MQTT_PORT, MQTT_USERNAME,
                    MSP01_ENABLED, MSP01_FRIDGE_ID, MSP01_TOPIC)
from mail.send_email import send_temperature_alert
from models.fridge import Fridge
from models.reading import save_reading, to_number
from models.room import save_motion, save_room_reading

log = logging.getLogger(__name__)

# How often to save a reading (seconds)
SAVE_EVERY = 60

# The MSP01 sends motion for 3 s each time. Motion this close together counts as one visit (seconds)
MOTION_HOLD = 30


# Receives the fridge readings over MQTT and sends the alerts
class MqttController:
    def __init__(self):
        # Filled in by load_fridges() when the app starts, from the Fridge table
        self.fridges = []
        self.msp01_fridge = None
        self.readings = {}
        self.alert_sent = {}
        self.alerts = {}
        self.last_saved = {}

        # Is the app connected to the MQTT broker right now? The Fridges page shows it
        self.connected = False

        # The MSP01 sensor (in Fridge 3). bright is 1 or 0 when it only knows light or dark
        self.room = {"temperature": None, "humidity": None, "light": None, "bright": None,
                     "battery": None, "rssi": None, "updated": None, "last_motion": None}
        self.room_last_saved = 0

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        # The broker's username and password, if it has one (see config.py)
        if MQTT_USERNAME:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    # Every fridge in the database. The ESP32 sends "frigN/temperature"; the MSP01's fridge uses "msp01/..."
    def load_fridges(self):
        self.fridges = Fridge.get_all()
        for fridge in self.fridges:
            if MSP01_ENABLED and fridge.id == MSP01_FRIDGE_ID:
                self.msp01_fridge = fridge
            self.readings[fridge.id] = {"temperature": None, "humidity": None, "updated": None}
            self.alert_sent[fridge.id] = False
            self.alerts[fridge.id] = None
            self.last_saved[fridge.id] = 0

    # Subscribe to the sensor topics
    def on_connect(self, client, userdata, flags, reason_code, properties):
        log.info("Connected to the MQTT broker: %s", reason_code)
        self.connected = not reason_code.is_failure
        for fridge in self.fridges:
            # The MSP01's fridge gets its readings from "msp01/#" below
            if fridge is not self.msp01_fridge:
                client.subscribe(fridge.temp_topic)
                client.subscribe(fridge.hum_topic)
        if MSP01_ENABLED:
            # Every topic under "msp01/", like "msp01/temperature"
            client.subscribe(f"{MSP01_TOPIC}/#")

    # paho tries again by itself, every few seconds
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        log.warning("Lost the MQTT broker (%s). Trying again...", reason_code)

    # A sensor reading. If anything goes wrong it is logged, so one bad message can't stop MQTT
    def on_message(self, client, userdata, msg):
        try:
            value = msg.payload.decode(errors="replace").strip()

            # The MSP01 sensor (in Fridge 3), like "msp01/humidity"
            if msg.topic.startswith(f"{MSP01_TOPIC}/"):
                self.on_room_message(msg.topic.split("/")[-1], value)
                return

            for fridge in self.fridges:
                if msg.topic == fridge.temp_topic:
                    self.on_fridge_reading(fridge, "temperature", value)
                elif msg.topic == fridge.hum_topic:
                    self.on_fridge_reading(fridge, "humidity", value)
        except Exception:
            log.exception("Could not handle the MQTT message on %s", msg.topic)

    # A fridge's temperature or humidity, from the ESP32 or the MSP01
    def on_fridge_reading(self, fridge, name, value):
        number = to_number(value)
        if number is None:
            return
        self.readings[fridge.id][name] = number
        self.readings[fridge.id]["updated"] = time.time()
        if name == "temperature":
            self.check_temperature(fridge, number)
            self.save_if_due(fridge)

    # One reading from the MSP01 sensor (in Fridge 3). name is "temperature", "humidity", "light", "bright", "battery", "rssi" or "motion"
    def on_room_message(self, name, value):
        number = to_number(value)
        if number is None:
            return
        now = time.time()
        self.room["updated"] = now

        # The MSP01's fridge: same limit, alerts and history as the other fridges
        if self.msp01_fridge is not None:
            if name in ("temperature", "humidity"):
                self.on_fridge_reading(self.msp01_fridge, name, value)
            else:
                # Any message means the sensor is still there, so the fridge doesn't show "Offline"
                self.readings[self.msp01_fridge.id]["updated"] = now

        if name == "motion":
            if number == 1:
                # A new visit if nobody moved in the last MOTION_HOLD seconds
                last = self.room["last_motion"]
                if last is None or now - last > MOTION_HOLD:
                    self.save_room(save_motion)
                self.room["last_motion"] = now
        elif name in ("temperature", "humidity", "light", "bright", "battery", "rssi"):
            self.room[name] = number

        # Save the room at most once a minute, once the temperature and humidity have come in
        has_both = self.room["temperature"] is not None and self.room["humidity"] is not None
        if now - self.room_last_saved >= SAVE_EVERY and has_both:
            self.room_last_saved = now
            self.save_room(save_room_reading, self.room["temperature"], self.room["humidity"], self.room["light"])

    # Run a save without stopping MQTT if the database has a problem
    def save_room(self, save, *args):
        try:
            save(*args)
        except sqlite3.Error as err:
            # like "no such table: RoomReading" if init_database wasn't run again
            log.error("Could not save the MSP01 reading: %s", err)

    # Email once when a fridge goes over its threshold, and again only after it has cooled down
    def check_temperature(self, fridge, temperature):
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

    # Is this fridge warmer than its limit right now? read_email.py asks before turning the fan on
    def is_too_warm(self, fridge_id):
        temperature = self.readings.get(fridge_id, {}).get("temperature")
        fridge = Fridge.get_by_id(fridge_id)
        if temperature is None or fridge is None or fridge.threshold is None:
            return False
        return temperature > fridge.threshold

    # Save at most one reading every SAVE_EVERY seconds
    def save_if_due(self, fridge):
        now = time.time()
        if now - self.last_saved[fridge.id] < SAVE_EVERY:
            return
        data = self.readings[fridge.id]
        if data["temperature"] is None:
            return
        try:
            save_reading(fridge.id, data["temperature"], data["humidity"])
            self.last_saved[fridge.id] = now
        except sqlite3.Error as err:
            # like "no such table: Reading" if init_database wasn't run again
            log.error("Could not save the reading for Frig%s: %s", fridge.id, err)

    # Runs in a thread. Records whether the email went out, for the dashboard
    def send_alert(self, fridge_id, temperature, threshold):
        sent = send_temperature_alert(fridge_id, temperature, threshold)
        self.alerts[fridge_id] = {
            "status": "sent" if sent else "failed",
            "email": ALERT_TO,
            "time": datetime.now().strftime("%H:%M"),
        }

    # Listen in a background thread. connect_async doesn't wait for the broker, so the website
    # still starts when the broker is down, and paho keeps trying until it is back
    def start(self):
        self.load_fridges()
        self.client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    # Stop listening and disconnect
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


# Shared by the routes and app.py
mqtt_controller = MqttController()
