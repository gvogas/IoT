import RPi.GPIO as GPIO

# Use the GPIO numbers, not the order of the pins on the board
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


class Fan:

    def __init__(self, enable_pin, input_pin, input2_pin):
        self.enable_pin = enable_pin
        self.input_pin = input_pin
        self.input2_pin = input2_pin

        GPIO.setup(self.enable_pin, GPIO.OUT)
        GPIO.setup(self.input_pin, GPIO.OUT)
        GPIO.setup(self.input2_pin, GPIO.OUT)

        # Start with the fan off
        self.off()

    def on(self):
        GPIO.output(self.input_pin, GPIO.LOW)     # which way it spins
        GPIO.output(self.input2_pin, GPIO.HIGH)   # which way it spins
        GPIO.output(self.enable_pin, GPIO.HIGH)   # power on

    def off(self):
        GPIO.output(self.enable_pin, GPIO.LOW)    # power off
