import math
import time

from flask import Blueprint, jsonify, render_template, request

from config import MSP01_ENABLED, MSP01_FRIDGE_ID
from controllers.mqtt_controller import mqtt_controller
from models.fridge import Fridge
from models.reading import get_history, get_stats, to_number
from routes.guards import admin_api, admin_page

fridge_routes = Blueprint("fridge_routes", __name__)

# How far back the history chart can go
HISTORY_HOURS = (1, 24, 168)

# The lowest and highest temperature limit an admin can set (°C)
MIN_LIMIT = -30
MAX_LIMIT = 30


# All the fridges
@fridge_routes.route("/fridges")
@admin_page
def fridges():
    return render_template("fridges/dashboard.html")


# One fridge with its gauges and history
@fridge_routes.route("/fridges/<int:fridge_id>")
@admin_page
def fridge_detail(fridge_id):
    fridge = Fridge.get_by_id(fridge_id)
    if fridge is None:
        return render_template("error.html", title="Fridge not found", text=f"Fridge {fridge_id} not found."), 404
    return render_template("fridges/detail.html", fridge=fridge)


# "MSP01" or "ESP32": what to check when the sensor stops sending
def sensor_name(fridge_id):
    return "MSP01" if MSP01_ENABLED and fridge_id == MSP01_FRIDGE_ID else "ESP32"


# The live data for one fridge
def fridge_data(fridge):
    data = mqtt_controller.readings.get(fridge.id, {})
    updated = data.get("updated")
    return {
        "id": fridge.id,
        "name": fridge.name,
        "threshold": fridge.threshold,
        "sensor": sensor_name(fridge.id),
        "temperature": to_number(data.get("temperature")),
        "humidity": to_number(data.get("humidity")),
        # seconds since the last reading
        "age": round(time.time() - updated) if updated else None,
        "alert": mqtt_controller.alerts.get(fridge.id),
        "stats": get_stats(fridge.id, fridge.threshold),
    }


# The fridge pages ask for this every 2 seconds
@fridge_routes.route("/api/fridges")
@admin_api
def api_fridges():
    return jsonify([fridge_data(fridge) for fridge in Fridge.get_all()])


# The live data for one fridge
@fridge_routes.route("/api/fridges/<int:fridge_id>")
@admin_api
def api_fridge(fridge_id):
    fridge = Fridge.get_by_id(fridge_id)
    if fridge is None:
        return jsonify(error=f"Fridge {fridge_id} not found."), 404
    return jsonify(fridge_data(fridge))


# Saved readings for the history chart
@fridge_routes.route("/api/fridges/<int:fridge_id>/history")
@admin_api
def api_history(fridge_id):
    hours = request.args.get("hours", 24, type=int)
    if hours not in HISTORY_HOURS:
        return jsonify(error=f"hours must be one of {HISTORY_HOURS}"), 400
    return jsonify(get_history(fridge_id, hours))


# Change a fridge's temperature limit
@fridge_routes.route("/api/fridges/<int:fridge_id>/threshold", methods=["POST"])
@admin_api
def set_threshold(fridge_id):
    try:
        threshold = float(request.form.get("threshold", ""))
    except ValueError:
        return jsonify(error="Please enter a number."), 400
    if not math.isfinite(threshold) or not MIN_LIMIT <= threshold <= MAX_LIMIT:
        return jsonify(error=f"The limit must be between {MIN_LIMIT} and {MAX_LIMIT} °C."), 400

    if not Fridge(fridge_id).set_threshold(threshold):
        return jsonify(error=f"Fridge {fridge_id} not found."), 404
    return jsonify(success=f"Threshold set to {threshold}"), 200
