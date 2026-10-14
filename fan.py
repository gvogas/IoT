import RPi.GPIO as GPIO
from time import sleep

# Use the GPIO numbers (BCM), not the physical pin numbers
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


class Fan:

    # Runs once when you make a fan: Fan(22, 27, 17)
    def __init__(self, enable_pin, input_pin, input2_pin):
        # Remember the pins so on() and off() can use them
        self.enable_pin = enable_pin
        self.input_pin = input_pin
        self.input2_pin = input2_pin

        # Set all 3 pins as outputs
        GPIO.setup(self.enable_pin, GPIO.OUT)
        GPIO.setup(self.input_pin, GPIO.OUT)
        GPIO.setup(self.input2_pin, GPIO.OUT)

        # Start with the fan off
        self.off()

    # Turn the fan on
    def on(self):
        GPIO.output(self.input_pin, GPIO.LOW)     # direction
        GPIO.output(self.input2_pin, GPIO.HIGH)   # direction
        GPIO.output(self.enable_pin, GPIO.HIGH)   # power on

    # Turn the fan off
    def off(self):
        GPIO.output(self.enable_pin, GPIO.LOW)    # power off

    # Call this when the program ends
    def cleanup(self):
        self.off()
        GPIO.cleanup()
