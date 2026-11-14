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

# The broker's username and password (from mosquitto_passwd, see docs/fridges.md).
# Leave both empty if the broker doesn't ask for a password
MQTT_USERNAME = ""
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

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


# ---------- RFID reader (CF600) ----------

# The reader's USB serial port. Change it to /dev/ttyACM0 if that is what shows up
RFID_PORT = "/dev/ttyUSB0"

# The CF600's serial baud rate
RFID_BAUD = 115200


# ---------- Fridge 3 sensor (Minew MSP01: temperature, humidity, light and motion over Bluetooth) ----------

# False = don't listen for the MSP01 and hide its cards on the dashboard
MSP01_ENABLED = False

# The sensor's Bluetooth address, printed on its back (like "AC:23:3F:AB:7F:00").
# Leave it empty to use the first MSP01 the Pi hears (its address is printed when the app starts)
MSP01_ADDRESS = ""

# The readings are published as msp01/temperature, msp01/humidity, msp01/light, msp01/motion, ...
MSP01_TOPIC = "msp01"

# The MSP01 sits in this fridge. Its temperature and humidity show up as this fridge on the
# Fridges page, with a limit and alert emails like the others (tools/init_database.py adds it)
MSP01_FRIDGE_ID = 3
