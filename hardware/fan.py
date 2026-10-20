import RPi.GPIO as GPIO

# Use the GPIO numbers, not the order of the pins on the board
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


class Fan:

    def __init__(fan, enable_pin, input_pin, input2_pin):
        # Remember the pins so on() and off() can use them
        fan.enable_pin = enable_pin
        fan.input_pin = input_pin
        fan.input2_pin = input2_pin

        # Set all 3 pins as outputs
        GPIO.setup(fan.enable_pin, GPIO.OUT)
        GPIO.setup(fan.input_pin, GPIO.OUT)
        GPIO.setup(fan.input2_pin, GPIO.OUT)

        # Start with the fan off
        fan.off()

    # Turn the fan on
    def on(fan):
        GPIO.output(fan.input_pin, GPIO.LOW)     # which way it spins
        GPIO.output(fan.input2_pin, GPIO.HIGH)   # which way it spins
        GPIO.output(fan.enable_pin, GPIO.HIGH)   # power on

    # Turn the fan off
    def off(fan):
        GPIO.output(fan.enable_pin, GPIO.LOW)    # power off

    # Call this when the program ends
    def cleanup(fan):
        fan.off()
        GPIO.cleanup()
