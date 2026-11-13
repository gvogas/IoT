import RPi.GPIO as GPIO

# Use the GPIO numbers, not the order of the pins on the board
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# The fan, wired through a motor driver
class Fan:

    def __init__(self, enable_pin, input_pin, input2_pin):
        self.enable_pin = enable_pin
        self.input_pin = input_pin
        self.input2_pin = input2_pin

        GPIO.setup(self.enable_pin, GPIO.OUT)
        GPIO.setup(self.input_pin, GPIO.OUT)
        GPIO.setup(self.input2_pin, GPIO.OUT)

        self.off()

    # Spin the fan
    def on(self):
        # The two inputs set which way it spins
        GPIO.output(self.input_pin, GPIO.LOW)
        GPIO.output(self.input2_pin, GPIO.HIGH)
        GPIO.output(self.enable_pin, GPIO.HIGH)

    # Stop the fan
    def off(self):
        GPIO.output(self.enable_pin, GPIO.LOW)
