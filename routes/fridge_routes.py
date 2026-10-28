from flask import Blueprint, jsonify, render_template, request
import sqlite3
import time

from models.fridge import Fridge
from models.reading import get_history, get_stats, to_number
from routes.auth_routes import is_admin
from controllers.mqtt_controller import mqtt_controller

# The fridge pages. app.py adds them with app.register_blueprint(fridge_routes)
fridge_routes = Blueprint("fridge_routes", __name__)

# How far back the history chart can go
HISTORY_HOURS = (1, 24, 168)


# -------------------------
# Fridge pages
# -------------------------

@fridge_routes.route("/fridges")
def fridges():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    return render_template("fridge_dashboard.html")


@fridge_routes.route("/fridges/<int:fridge_id>")
def fridge_detail(fridge_id):
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        fridge = Fridge.get_by_id(fridge_id)
    except sqlite3.Error as err:
        return f"Database error: {err}", 500
    if fridge is None:
        return f"Fridge {fridge_id} not found.", 404

    return render_template("fridge_detail.html", fridge=fridge)


# The data for one fridge
def fridge_data(fridge):
    data = mqtt_controller.readings.get(fridge.id, {})
    updated = data.get("updated")
    return {
        "id": fridge.id,
        "name": fridge.name,
        "threshold": fridge.threshold,
        "temperature": to_number(data.get("temperature")),
        "humidity": to_number(data.get("humidity")),
        # seconds since the last reading
        "age": round(time.time() - updated) if updated else None,
        "alert": mqtt_controller.alerts.get(fridge.id),
        "stats": get_stats(fridge.id, fridge.threshold),
    }


# Newest readings for all fridges. The page asks for this every 2 seconds
@fridge_routes.route("/api/fridges")
def api_fridges():
    if not is_admin():
        return jsonify(error="Only admins can see this."), 403

    try:
        result = [fridge_data(fridge) for fridge in Fridge.get_all()]
    except sqlite3.Error as err:
        # like "no such table: Fridge" if you forgot to run python -m tools.init_database
        return jsonify(error=f"Database error: {err}"), 500
    return jsonify(result)


# Newest readings for one fridge
@fridge_routes.route("/api/fridges/<int:fridge_id>")
def api_fridge(fridge_id):
    if not is_admin():
        return jsonify(error="Only admins can see this."), 403

    try:
        fridge = Fridge.get_by_id(fridge_id)
        if fridge is None:
            return jsonify(error=f"Fridge {fridge_id} not found."), 404
        return jsonify(fridge_data(fridge))
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500


# Saved readings for the history chart
@fridge_routes.route("/api/fridges/<int:fridge_id>/history")
def api_history(fridge_id):
    if not is_admin():
        return jsonify(error="Only admins can see this."), 403

    hours = request.args.get("hours", 24, type=int)
    if hours not in HISTORY_HOURS:
        return jsonify(error=f"hours must be one of {HISTORY_HOURS}"), 400

    try:
        return jsonify(get_history(fridge_id, hours))
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500


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
