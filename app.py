import threading

import sqlite3

from flask import Flask, render_template

from config import FRIDGES_ENABLED, SECRET_KEY
from mail.read_email import check_forever

from controllers.mqtt_controller import mqtt_controller
from controllers.fan_controller import fan_controller
from hardware import signals
from models.customer import all_customers
from routes.auth_routes import auth_routes, is_admin, is_signed_in
from routes.customer_routes import customer_routes, show_account
from routes.fridge_routes import fridge_routes
from routes.fan_routes import fan_routes


app = Flask(__name__)
app.secret_key = SECRET_KEY   # Flask needs this so people can stay signed in

# The sign in and sign out pages are in routes/auth_routes.py
app.register_blueprint(auth_routes)

# The sign up page and the customer list are in routes/customer_routes.py
app.register_blueprint(customer_routes)
# The fridge page and the fridge data are in routes/fridge_routes.py
app.register_blueprint(fridge_routes)
app.register_blueprint(fan_routes)


# The main page. It is different for admins, customers and people not signed in
@app.route("/")
def home():
    if is_admin():
        try:
            customers = all_customers()
        except sqlite3.Error as err:
            return f"Database error: {err}", 500
        return render_template("admin_home.html", customer_count=len(customers))

    if is_signed_in():
        return show_account()

    return render_template("home.html")


# -------------------------
# Start Flask
# -------------------------

if __name__ == "__main__":

    try:
        if FRIDGES_ENABLED:
            # Start listening to the sensors while the website runs.
            mqtt_controller.start()

            # Check the inbox for YES/NO replies to alert emails while the website runs.
            threading.Thread(target=check_forever, daemon=True).start()

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False
        )

    finally:

        try:
            if FRIDGES_ENABLED:
                mqtt_controller.stop()
        finally:
            try:
                fan_controller.turn_off()
            finally:
                signals.cleanup()
