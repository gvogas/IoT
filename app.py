from flask import Flask, render_template, request
import sqlite3
import re

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
    sleep(5)
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

        return "ERROR: Please fill in all the fields.", 400


    # -------------------------
    # Check email
    # -------------------------

    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_regex, customer_email):

        send_error()

        return "ERROR: Please enter a valid email address.", 400


    # -------------------------
    # Check phone number
    # -------------------------

    phone_regex = r"^\+?[1-9]\d{7,14}$"

    if not re.match(phone_regex, customer_phone_number):

        send_error()

        return "ERROR: Please enter a valid phone number.", 400


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

        return "SUCCESS: Customer information was added successfully.", 200


    except sqlite3.IntegrityError:

        # Happens if email or phone number already exists

        send_error()

        return "ERROR: This email or phone number is already registered.", 400


    except sqlite3.Error as err:

        send_error()

        return f"ERROR: Database error: {err}", 400


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