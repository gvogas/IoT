import os
import secrets

# All the settings are here. If you need to change one, change it in this file.

# -------------------------
# Database
# -------------------------

# The database file. It holds the customers and the fridges. It is always store.db in the project folder.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.db")


# -------------------------
# Sign in (to make someone an admin, use tools/set_role.py)
# -------------------------

# A secret word Flask uses to keep people signed in.
# It is new every time the app starts, so a restart signs everyone out.
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(16)


# -------------------------
# MQTT broker (the program on the Pi that passes the sensor messages along)
# -------------------------

# school ip
MQTT_BROKER = "192.168.50.107"
# home
# MQTT_BROKER = "192.168.50.107"

MQTT_PORT = 1883


# -------------------------
# Raspberry Pi pins (use the GPIO numbers, not the order of the pins on the board)
# -------------------------

# Fan motor driver pins: enable, input, input2
FAN_PINS = (22, 27, 17)

LEDRED = 21
LEDBLUE = 26
BUZZER = 24


