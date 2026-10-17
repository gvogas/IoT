import RPi.GPIO as GPIO
from time import sleep

from config import LEDRED, LEDBLUE, BUZZER

# Use the GPIO numbers, not the order of the pins on the board
GPIO.setmode(GPIO.BCM)

GPIO.setup(LEDRED, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LEDBLUE, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(BUZZER, GPIO.OUT, initial=GPIO.LOW)


# -------------------------
# Success: turn on the blue light for 3 seconds
# -------------------------

def send_success():
    print("SUCCESS: Customer information is correct.")

    GPIO.output(LEDBLUE, GPIO.HIGH)
    sleep(3)
    GPIO.output(LEDBLUE, GPIO.LOW)


# -------------------------
# Error: turn on the red light and beep for 1 second
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


# Call this when the program ends
def cleanup():
    GPIO.cleanup()
