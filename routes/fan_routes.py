from flask import Blueprint, current_app, jsonify

from controllers.fan_controller import fan_controller
from controllers.mqtt_controller import mqtt_controller
from routes.guards import admin_api

fan_routes = Blueprint("fan_routes", __name__)


# "ON" or "OFF", and whether the app can reach the MQTT broker
@fan_routes.route("/api/fan")
@admin_api
def fan_status():
    return jsonify(state=fan_controller.get_state(), broker=mqtt_controller.connected)


# Turn the fan off from the fridge pages. Only a YES reply to the alert email turns it on
@fan_routes.route("/api/fan/off", methods=["POST"])
@admin_api
def turn_off():
    try:
        state = fan_controller.turn_off()
    except Exception:
        current_app.logger.exception("Unable to turn off the shared fan")
        return jsonify(error="Unable to turn off the fan.", state="UNKNOWN"), 503
    return jsonify(success="Fan turned off.", state=state)
