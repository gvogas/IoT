from flask import Flask, render_template, request
import sqlite3
import re #regex


#Board setup
import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)

#declare the pin for the LED and buzzer
LEDRED = 21
LEDBLUE = 26
BUZZER = 24

GPIO.setup(LEDRED, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LEDBLUE, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(BUZZER, GPIO.OUT, initial=GPIO.LOW)

# from Customer import customer_auth

app = Flask(__name__)

# app.register_blueprint(customer_auth)

def get_db_connection():
    conn = sqlite3.connect('customer.db')

    conn.row_factory = sqlite3.Row
    return conn


#helper methods to validate the input data
def send_error():
    #RED led on and Buzzer on
    GPIO.output(LEDRED, GPIO.HIGH)

    buzzer_pwm = GPIO.PWM(BUZZER, 2000)

    try:
        buzzer_pwm.start(50)  # 50% duty cycle
        sleep(1)
    finally:
        buzzer_pwm.stop()
        GPIO.output(LEDRED, GPIO.LOW)
        

@app.route("/")
def home():
    return render_template('customerDashboard.html')

@app.route('/submit', methods=['POST'])
def submit():
    customer_name = request.form.get("name", "").strip()
    customer_address = request.form.get("address", "").strip()
    customer_email = request.form.get("email", "").strip()
    customer_phone_number = request.form.get("phoneNumber", "").strip()

    # validate the data
    #If feilds are empty
    if not customer_name or not customer_address or not customer_email or not customer_phone_number:
        send_error()
        return "Please fill in all the fields", 400

    #validate the email
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_valid = bool(re.match(email_regex, customer_email))
    if not is_valid:
        send_error()
        return "Please enter a valid email address", 400

    #validate the phone number
    phone_regex = r"^\+?[1-9]\d{7,14}$"
    is_valid = bool(re.match(phone_regex, customer_phone_number))
    if not is_valid:
        send_error()
        return "Please enter a valid phone number", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "INSERT INTO Customer (customerName, address, email, phoneNumber) VALUES (?,?,?,?)"
        cursor.execute(query, (customer_name, customer_address, customer_email, customer_phone_number))

        conn.commit()

        #Data was successfully written to the database
        GPIO.output(LEDBLUE, GPIO.HIGH)
        sleep(5)
        GPIO.output(LEDBLUE, GPIO.LOW)
        return "Data successfully written", 200
    
    except sqlite3.Error as err:
        send_error()
        return f"An error occured: {err}",400
    
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)