from flask import Blueprint, jsonify, render_template, request
import sqlite3

from models.fridge import Fridge
from routes.auth_routes import is_admin
from controllers.mqtt_controller import mqtt_controller

# The fridge pages. app.py adds them with app.register_blueprint(fridge_routes)
fridge_routes = Blueprint("fridge_routes", __name__)


# -------------------------
# Fridge dashboard
# -------------------------

@fridge_routes.route("/fridges")
def fridges():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    return render_template("fridge_dashboard.html")


# Newest readings and thresholds. The page asks for this every 2 seconds
@fridge_routes.route("/api/fridges")
def api_fridges():
    if not is_admin():
        return jsonify(error="Only admins can see this."), 403

    try:
        fridges = Fridge.get_all()
        result = []
        for fridge in fridges:
            data = mqtt_controller.readings.get(fridge.id, {})
            result.append({
                "id": fridge.id,
                "name": fridge.name,
                "threshold": fridge.threshold,
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
            })
    except sqlite3.Error as err:
        # like "no such table: Fridge" if you forgot to run python -m tools.init_database
        return jsonify(error=f"Database error: {err}"), 500
    return jsonify(result)


# Change a fridge's threshold
@fridge_routes.route("/api/fridges/<int:fridge_id>/threshold", methods=["POST"])
def set_threshold(fridge_id):
    if not is_admin():
        return jsonify(error="Only admins can see this."), 403

    try:
        threshold = float(request.form.get("threshold", ""))
    except ValueError:
        return jsonify(error="Please enter a number."), 400

    try:
        found = Fridge(fridge_id).set_threshold(threshold)
    except sqlite3.Error as err:
        # like "database is locked" if DB Browser has changes that are not saved
        return jsonify(error=f"Database error: {err}"), 500

    if not found:
        return jsonify(error=f"Fridge {fridge_id} not found."), 404

    return jsonify(success=f"Threshold set to {threshold}"), 200
