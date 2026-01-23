import screen_brightness_control as sbc
from DataExchange import DataExchange
import subprocess
import os


class SystemControler():
    def __init__(self):
        self.config = DataExchange.get_config()

    def set_brightness(value):
        sbc.set_brightness(value)

    def open_application(app_path):
        pass
        
    def close_application(app_path):
        pass


SystemControler.set_brightness(100)