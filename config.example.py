import os
import secrets

# All the settings are here. If you need to change one, change it in this file.

# ---------- Database ----------

# The database file. It holds the store and the fridges. It is always store.db in the project folder.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.db")


# ---------- Sign in (tools/set_role.py makes someone an admin) ----------

# Keeps people signed in. A new one each start, so a restart signs everyone out
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(16)


# ---------- Fridges (Phase 2) ----------

# False runs the app without MQTT, the ESP32, the sensors or alert emails
FRIDGES_ENABLED = False


# ---------- MQTT broker (passes the sensor messages along) ----------

# IP of the Raspberry Pi running the broker
MQTT_BROKER = "192.168.0.100"

MQTT_PORT = 1883

# Send "ON" or "OFF" here to control the fan (a YES reply to an alert email sends "ON")
FAN_COMMAND_TOPIC = "fan/command"

# ---------- Email (fridge alerts go to ALERT_TO, stock alerts to the admins) ----------

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "you@gmail.com")
ALERT_EMAIL_PASSWORD = os.environ.get("ALERT_EMAIL_PASSWORD", "your-gmail-app-password")
ALERT_TO = os.environ.get("ALERT_TO", "alerts-go-here@gmail.com")

# Degrees below the threshold before another alert can be sent
ALERT_RESET_MARGIN = 1.0


# ---------- Raspberry Pi pins (GPIO numbers) ----------

# Fan motor driver pins: enable, input, input2
FAN_PINS = (22, 27, 17)

LEDRED = 21
LEDBLUE = 26
BUZZER = 24


# ---------- RFID reader (CF600) ----------

# The reader's USB serial port. Change it to /dev/ttyACM0 if that is what shows up
RFID_PORT = "/dev/ttyUSB0"

# The CF600's serial baud rate
RFID_BAUD = 115200
