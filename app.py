import threading

import sqlite3

from flask import Flask, render_template

from config import FRIDGES_ENABLED, SECRET_KEY
from mail.read_email import check_forever

from controllers.mqtt_controller import mqtt_controller
from controllers.fan_controller import fan_controller
from hardware import signals
from models.customer import all_customers
from models.product import all_products
from routes.auth_routes import auth_routes, is_admin
from routes.checkout_routes import checkout_routes
from routes.customer_routes import customer_routes
from routes.fridge_routes import fridge_routes
from routes.fan_routes import fan_routes
from routes.product_routes import product_routes


app = Flask(__name__)
app.secret_key = SECRET_KEY   # Flask needs this so people can stay signed in

# The sign in and sign out pages are in routes/auth_routes.py
app.register_blueprint(auth_routes)

# The checkout page (the main page), paying, and signing in with a barcode are in routes/checkout_routes.py
app.register_blueprint(checkout_routes)

# The sign up page and the customer list are in routes/customer_routes.py
app.register_blueprint(customer_routes)
# The fridge page and the fridge data are in routes/fridge_routes.py
app.register_blueprint(fridge_routes)
app.register_blueprint(fan_routes)
# The inventory, products and receiving pages are in routes/product_routes.py
app.register_blueprint(product_routes)


# The main page is the checkout. It is in routes/checkout_routes.py

# The admin page, with a card for each dashboard
@app.route("/admin")
def admin():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403
    try:
        customers = all_customers()
        products = all_products()
    except sqlite3.Error as err:
        return f"Database error: {err}", 500
    return render_template("admin_home.html", customer_count=len(customers), product_count=len(products))


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
