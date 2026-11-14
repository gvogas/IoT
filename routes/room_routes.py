import time

from flask import Blueprint, jsonify

from controllers.mqtt_controller import MOTION_HOLD, mqtt_controller
from models.room import get_room_stats
from routes.guards import admin_api

room_routes = Blueprint("room_routes", __name__)


# Seconds since a time.time(), or None
def seconds_since(when):
    return round(time.time() - when) if when else None


# The MSP01 sensor (in Fridge 3). The dashboard asks for this every 5 seconds
@room_routes.route("/api/room")
@admin_api
def api_room():
    room = mqtt_controller.room
    motion_age = seconds_since(room["last_motion"])
    return jsonify(
        temperature=room["temperature"],
        humidity=room["humidity"],
        light=room["light"],
        bright=room["bright"],
        battery=room["battery"],
        # signal strength in dBm
        rssi=room["rssi"],
        # seconds since the last message from the sensor
        age=seconds_since(room["updated"]),
        # Someone moved in the last MOTION_HOLD seconds
        motion=motion_age is not None and motion_age <= MOTION_HOLD,
        stats=get_room_stats(),
    )
