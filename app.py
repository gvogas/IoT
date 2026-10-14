from flask import Flask, jsonify, render_template, request
import sqlite3
import re
import paho.mqtt.client as mqtt

# Raspberry Pi
import RPi.GPIO as GPIO
from time import sleep


# -------------------------
# Raspberry Pi setup
# -------------------------

GPIO.setmode(GPIO.BCM)

LEDRED = 21
LEDBLUE = 26
BUZZER = 24

GPIO.setup(LEDRED, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LEDBLUE, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(BUZZER, GPIO.OUT, initial=GPIO.LOW)


app = Flask(__name__)


# -------------------------
# MQTT: keep the latest fridge readings
# -------------------------

MQTT_BROKER = "192.168.50.107"

# Latest values, e.g. readings[1]["temperature"]
readings = {
    1: {"temperature": None, "humidity": None, "fan": "OFF"},
    2: {"temperature": None, "humidity": None, "fan": "OFF"},
}

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("frig1/#")
    client.subscribe("frig2/#")

# Topics look like "frig1/temperature", "frig2/humidity", "frig1/fan"
def on_mqtt_message(client, userdata, msg):
    fridge, kind = msg.topic.split("/")
    fridge_id = int(fridge.replace("frig", ""))
    if fridge_id in readings and kind in readings[fridge_id]:
        readings[fridge_id][kind] = msg.payload.decode().strip()

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()  # runs in the background next to Flask


# -------------------------
# Database connection
# -------------------------

def get_db_connection():
    conn = sqlite3.connect('customer.db')
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# Success signal
# -------------------------

def send_success():
    print("SUCCESS: Customer information is correct.")

    GPIO.output(LEDBLUE, GPIO.HIGH)
    sleep(3)
    GPIO.output(LEDBLUE, GPIO.LOW)


# -------------------------
# Error signal
# -------------------------

def send_error():
    print("ERROR: Customer information is not correct.")

    GPIO.output(LEDRED, GPIO.HIGH)

    buzzer_pwm = GPIO.PWM(BUZZER, 2000)

    try:
        buzzer_pwm.start(50)
        sleep(1)
    finally:
        buzzer_pwm.stop()
        GPIO.output(LEDRED, GPIO.LOW)


# -------------------------
# Home page
# -------------------------

@app.route("/")
def home():
    return render_template("customerDashboard.html")


# -------------------------
# Fridge dashboard
# -------------------------

@app.route("/fridges")
def fridges():
    return render_template("fridgeDashboard.html")


# Latest readings + thresholds, the page asks for this every 2 seconds
@app.route("/api/fridges")
def api_fridges():
    conn = get_db_connection()
    rows = conn.execute("SELECT fridgeID, fridgeName, temp_threshold FROM Fridge").fetchall()
    conn.close()

    result = []
    for row in rows:
        data = readings.get(row["fridgeID"], {})
        result.append({
            "id": row["fridgeID"],
            "name": row["fridgeName"],
            "threshold": row["temp_threshold"],
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "fan": data.get("fan"),
        })
    return jsonify(result)


# Change a fridge's threshold
@app.route("/api/fridges/<int:fridge_id>/threshold", methods=["POST"])
def set_threshold(fridge_id):
    try:
        threshold = float(request.form.get("threshold", ""))
    except ValueError:
        return jsonify(error="Please enter a number."), 400

    conn = get_db_connection()
    conn.execute("UPDATE Fridge SET temp_threshold = ? WHERE fridgeID = ?", (threshold, fridge_id))
    conn.commit()
    conn.close()

    return jsonify(success=f"Threshold set to {threshold}"), 200


# -------------------------
# Submit customer
# -------------------------

@app.route("/submit", methods=["POST"])
def submit():

    customer_name = request.form.get("name", "").strip()
    customer_address = request.form.get("address", "").strip()
    customer_email = request.form.get("email", "").strip()
    customer_phone_number = request.form.get("phoneNumber", "").strip()


    # -------------------------
    # Check empty fields
    # -------------------------

    if not customer_name or not customer_address or not customer_email or not customer_phone_number:

        send_error()

        return jsonify(error="Please fill in all the fields."), 400


    # -------------------------
    # Check email
    # -------------------------

    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_regex, customer_email):

        send_error()

        return jsonify(error="Please enter a valid email address."), 400


    # -------------------------
    # Check phone number
    # -------------------------

    phone_regex = r"^\+?[1-9]\d{7,14}$"

    if not re.match(phone_regex, customer_phone_number):

        send_error()

        return jsonify(error="Please enter a valid phone number."), 400


    # -------------------------
    # Add customer to database
    # -------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        query = """
        INSERT INTO Customer
        (customerName, address, email, phoneNumber)
        VALUES (?, ?, ?, ?)
        """

        cursor.execute(
            query,
            (
                customer_name,
                customer_address,
                customer_email,
                customer_phone_number
            )
        )

        conn.commit()

        # -------------------------
        # SUCCESS
        # -------------------------

        send_success()

        return jsonify(success="Customer information was added successfully."), 200


    except sqlite3.IntegrityError:

        # Happens if email or phone number already exists

        send_error()

        return jsonify(error="This email or phone number is already registered."), 400


    except sqlite3.Error as err:

        send_error()

        return jsonify(error=f"Database error: {err}"), 400


    finally:

        cursor.close()
        conn.close()


# -------------------------
# Start Flask
# -------------------------

if __name__ == "__main__":

    try:

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False
        )

    finally:

        GPIO.cleanup()