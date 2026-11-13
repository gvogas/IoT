"""Controls the one shared fan."""

from config import FAN_PINS
from hardware.fan import Fan


# Keeps track of whether the shared fan is on
class FanController:
    def __init__(self):
        self.fan = Fan(*FAN_PINS)
        self.state = "OFF"

    # "ON" or "OFF"
    def get_state(self):
        return self.state

    def turn_on(self):
        self.fan.on()
        self.state = "ON"
        return self.state

    def turn_off(self):
        self.fan.off()
        self.state = "OFF"
        return self.state


# Shared by the routes and the MQTT controller
fan_controller = FanController()
