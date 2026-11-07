import threading

from flask import Flask

from config import FRIDGES_ENABLED, SECRET_KEY
from controllers.fan_controller import fan_controller
from controllers.mqtt_controller import mqtt_controller
from hardware import signals
from mail.read_email import check_forever
from models.product_image import MAX_UPLOAD_BYTES
from routes import register_routes

app = Flask(__name__)
app.secret_key = SECRET_KEY   # Flask needs this so people can stay signed in
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
register_routes(app)


if __name__ == "__main__":
    try:
        if FRIDGES_ENABLED:
            # Listen to the sensors, and check the inbox for YES/NO replies to alert emails
            mqtt_controller.start()
            threading.Thread(target=check_forever, daemon=True).start()

        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

    finally:
        # Don't leave the fan spinning or the pins set after the app is gone
        try:
            if FRIDGES_ENABLED:
                mqtt_controller.stop()
        finally:
            try:
                fan_controller.turn_off()
            finally:
                signals.cleanup()
