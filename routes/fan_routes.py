from flask import Blueprint, current_app, jsonify

from controllers.fan_controller import fan_controller
from routes.auth_routes import is_admin

fan_routes = Blueprint("fan_routes", __name__)


@fan_routes.route("/api/fan")
def fan_status():
    if not is_admin():
        return jsonify(error="Only admins can see this."), 403
    return jsonify(state=fan_controller.get_state())


@fan_routes.route("/api/fan/off", methods=["POST"])
def turn_off():
    if not is_admin():
        return jsonify(error="Only admins can control the fan."), 403
    try:
        state = fan_controller.turn_off()
    except Exception:
        current_app.logger.exception("Unable to turn off the shared fan")
        return jsonify(error="Unable to turn off the fan.", state="UNKNOWN"), 503
    return jsonify(success="Fan turned off.", state=state)
