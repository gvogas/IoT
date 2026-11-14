import logging
import os
import threading
from logging.handlers import RotatingFileHandler

from flask import Flask

from config import FRIDGES_ENABLED, MSP01_ENABLED, SECRET_KEY
from controllers.fan_controller import fan_controller
from controllers.mqtt_controller import mqtt_controller
from hardware import fan, msp01
from hardware.rfid import setup_reader
from mail.read_email import check_forever
from models.product_image import MAX_UPLOAD_BYTES
from routes import register_routes

# Log to the screen and to logs/app.log, with the time and level on each line.
# The file is kept under 1 MB; the 5 older files are app.log.1 to app.log.5
LOG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_FOLDER, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(os.path.join(LOG_FOLDER, "app.log"), maxBytes=1_000_000, backupCount=5),
    ],
)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
register_routes(app)


if __name__ == "__main__":
    try:
        # Make /dev/ttyUSB0 show up for the RFID reader (only needed after a reboot)
        setup_reader()

        # Listen to the sensors over MQTT
        if FRIDGES_ENABLED or MSP01_ENABLED:
            mqtt_controller.start()

        # Check the inbox for YES/NO replies to fridge alert emails
        if FRIDGES_ENABLED:
            threading.Thread(target=check_forever, daemon=True).start()

        # Hear the MSP01 sensor (in Fridge 3) over Bluetooth (msp01/index.js) and pass its readings to MQTT
        if MSP01_ENABLED:
            msp01.start()

        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

    finally:
        # Don't leave the fan spinning or the pins set after the app is gone
        try:
            if MSP01_ENABLED:
                msp01.stop()
            if FRIDGES_ENABLED or MSP01_ENABLED:
                mqtt_controller.stop()
        finally:
            try:
                fan_controller.turn_off()
            finally:
                fan.cleanup()
