"""Controls the one shared fan."""

from config import FAN_PINS
from hardware.fan import Fan


class FanController:
    def __init__(self):
        self.fan = Fan(*FAN_PINS)
        self.state = "OFF"

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


# Routes share this controller and its single fan.
fan_controller = FanController()
