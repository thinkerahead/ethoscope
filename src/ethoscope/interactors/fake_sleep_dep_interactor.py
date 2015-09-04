__author__ = 'quentin'

from sleep_depriver_interactor import SleepDepInteractor, HasInteractedVariable
from ethoscope.hardware.interfaces.fake_sleep_dep_interface import FakeSleepDepriverInterface
import sys

class FakeSleepDepInteractor(SleepDepInteractor):
    description = {"overview": "A dummy interactor that simply print messages instead of moving tubes. For development only",
                    "arguments": [
                                    {"type": "number", "min": 0.0, "max": 1.0, "step":0.0001, "name": "velocity_threshold", "description": "The minimal velocity that counts as movement","default":0.0060},
                                    {"type": "number", "min": 1, "max": 3600*12, "step":1, "name": "min_inactive_time", "description": "The minimal time after which an inactive animal is awaken","default":120},
                                    {"type": "datetime", "name": "start_datetime", "description": "When sleep deprivation is to be started","default":0},
                                    {"type": "datetime", "name": "end_datetime", "description": "When sleep deprivation is to be ended","default":sys.maxsize}
                                   ]}
    _hardwareInterfaceClass = FakeSleepDepriverInterface




