"""Starts and stops the program that hears the Minew MSP01 sensor in Fridge 3.

That program is msp01/index.js. It is written in JavaScript because it uses reelyActive's
barnowl package (github.com/reelyactive/barnowl) to listen on the Pi's Bluetooth, and
their advlib package to decode the sensor's packets. It publishes the readings to MQTT,
like "msp01/temperature" -> "22.0", and MqttController receives them from there.

Setup, once (see the README):
    cd msp01
    npm install
    npm run privileges     (lets Node use Bluetooth without sudo)
"""

import logging
import os
import subprocess

from config import MQTT_BROKER, MQTT_PASSWORD, MQTT_PORT, MQTT_USERNAME, MSP01_ADDRESS, MSP01_TOPIC

# msp01/index.js, next to this project's other folders
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "msp01", "index.js")

log = logging.getLogger(__name__)

# The running program, or None
process = None


# Start msp01/index.js in the background, with the settings from config.py
def start():
    global process
    settings = dict(os.environ, MQTT_BROKER=MQTT_BROKER, MQTT_PORT=str(MQTT_PORT),
                    MSP01_ADDRESS=MSP01_ADDRESS, MSP01_TOPIC=MSP01_TOPIC,
                    MQTT_USERNAME=MQTT_USERNAME, MQTT_PASSWORD=MQTT_PASSWORD)
    try:
        process = subprocess.Popen(["node", SCRIPT], env=settings)
    except FileNotFoundError:
        log.error("Can't hear the MSP01: Node.js is not installed (sudo apt install nodejs npm)")


# Stop it when the app stops
def stop():
    if process is not None:
        process.terminate()
