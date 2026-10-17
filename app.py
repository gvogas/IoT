from flask import Flask, render_template

from config import SECRET_KEY

import mqtt_server
from hardware import signals
from routes.auth_routes import auth_routes
from routes.customer_routes import customer_routes
from routes.fridge_routes import fridge_routes


app = Flask(__name__)
app.secret_key = SECRET_KEY   # Flask needs this so people can stay signed in

# The sign in and sign out pages are in routes/auth_routes.py
app.register_blueprint(auth_routes)

# The sign up page and the customer list are in routes/customer_routes.py
app.register_blueprint(customer_routes)
# The fridge page and the fridge data are in routes/fridge_routes.py
app.register_blueprint(fridge_routes)


# The main page. It has a link to each dashboard.
@app.route("/")
def home():
    return render_template("home.html")


# -------------------------
# Start Flask
# -------------------------

if __name__ == "__main__":

    # Start listening to the sensors and controlling the fan. It keeps going while the website runs.
    mqtt_server.start()

    try:

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False
        )

    finally:

        mqtt_server.stop()
        signals.cleanup()
