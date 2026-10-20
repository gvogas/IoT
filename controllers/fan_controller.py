"""Controls the one shared fan."""

from config import FAN_PINS
from hardware.fan import Fan


class FanController:
    def __init__(fan):
        fan = Fan(*FAN_PINS)
        state = "OFF"

    def get_state(fan):
        return self.state

    def turn_off(self):
        self.fan.off()
        self.state = "OFF"
        return self.state


# Routes share this controller and its single fan.
fan_controller = FanController()
