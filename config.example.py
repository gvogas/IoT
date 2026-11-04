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
# Fridges (Phase 2)
# -------------------------

# False = don't connect to MQTT or check alert emails, so the app runs
# without the broker, the ESP32 or the sensors
FRIDGES_ENABLED = False


# -------------------------
# MQTT broker (the program on the Pi that passes the sensor messages along)
# -------------------------

# IP of the Raspberry Pi running the broker
MQTT_BROKER = "192.168.0.100"

MQTT_PORT = 1883

# Send "ON" or "OFF" here to control the fan (a YES reply to an alert email sends "ON")
FAN_COMMAND_TOPIC = "fan/command"

# -------------------------
# Email alerts (sent when a fridge goes over its threshold)
# -------------------------

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "you@gmail.com")
ALERT_EMAIL_PASSWORD = os.environ.get("ALERT_EMAIL_PASSWORD", "your-gmail-app-password")
ALERT_TO = os.environ.get("ALERT_TO", "alerts-go-here@gmail.com")

# After an alert, the fridge must cool this many degrees below the threshold
# before another alert can be sent (stops a flood of emails near the threshold)
ALERT_RESET_MARGIN = 1.0


# -------------------------
# Raspberry Pi pins (use the GPIO numbers, not the order of the pins on the board)
# -------------------------

# Fan motor driver pins: enable, input, input2
FAN_PINS = (22, 27, 17)

LEDRED = 21
LEDBLUE = 26
BUZZER = 24


# -------------------------
# RFID reader (CF600, used to scan the EPC of each unit when receiving stock)
# -------------------------

# The reader's USB serial port. Change it to /dev/ttyACM0 if that is what shows up
RFID_PORT = "/dev/ttyUSB0"

# The CF600's serial baud rate
RFID_BAUD = 115200
