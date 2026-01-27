import screen_brightness_control as sbc
import DataExchange 
import subprocess
import os

import shutil



class SystemControler():
    def __init__(self):
        self.config = DataExchange.get_config()

    def set_brightness(value):
        sbc.set_brightness(sbc.get_brightness()[0] + value)

    def open_application(app_path):
        path = shutil.which(app_path)
        print(path)
        
    def close_application(app_path):
        pass
    def set_volume(value):
        pass


    def classify_action(classify_config):
        if classify_config["action"] == "increase":
            if classify_config["component"] == "volume":
                value = int(classify_config["value"])
                SystemControler.set_volume(value)

            elif classify_config["component"] == "brightness":
                value = int(classify_config["value"])
                if value > sbc.get_brightness()[0]: value = sbc.get_brightness()[0]
                SystemControler.set_brightness(value)
        elif classify_config["action"] == "decrease":
            if classify_config["component"] == "volume":
                value = -1 * int(classify_config["value"])

                SystemControler.set_volume(value)
            elif classify_config["component"] == "brightness":
                value = -1 * int(classify_config["value"])
                if -1 * value > sbc.get_brightness()[0]: value = sbc.get_brightness()[0]
                SystemControler.set_brightness(value)
        elif classify_config["action"] == "open":
            pass
            


SystemControler.open_application("chrome.exe")