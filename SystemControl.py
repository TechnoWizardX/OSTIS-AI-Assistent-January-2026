import screen_brightness_control as sbc
import subprocess
import os
import webbrowser
import json

class SystemControler():
    
    @staticmethod
    def set_brightness(value):
        sbc.set_brightness(sbc.get_brightness()[0] + value)

    @staticmethod
    def open_application(app_path):
        path = SystemControler.find_exe(app_path)
        if path == None:
            path = SystemControler.find_exe(app_path, "D:\\")
        
        try:
            os.startfile(path)
        except Exception as e:
            print(f"Ошибка открытия приложения: {e}")

    @staticmethod
    def close_application(app_path):
        try:
            if app_path != "explorer.exe":
                subprocess.call(f'taskkill /F /IM {app_path}', shell=True)
        except Exception as e:
            print(f"Ошибка закрытия приложения: {e}")

    @staticmethod
    def get_name_exe_pair():
        with open("name_exe_pair.json", "r", encoding="utf-8") as file:
            return json.load(file)
        
    @staticmethod
    def find_exe(filename, search_path="C:\\"):
        matches = []
        exe_name = SystemControler.get_name_exe_pair()[filename]
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if file.lower() == exe_name.lower():
                    matches.append(os.path.join(root, file))
                    print(matches[0])
                    break
        if matches:
            return matches[0]
        else:
            return None
    @staticmethod
    def open_website(website):
        webbrowser.open(f"https://www.google.com/search?q={website}")

    @staticmethod
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
            if classify_config["component"] == "website":
                SystemControler.open_website(classify_config["value"])

            elif classify_config["component"] == "application":
                SystemControler.open_application(classify_config["value"])

        elif classify_config["action"] == "close":
            if classify_config["component"] == "website":
                SystemControler.close_application("chrome.exe")

            elif classify_config["component"] == "application":
                SystemControler.close_application(classify_config["value"])
            

answer = {"message_to_user" : "Здесь будет ответ от NIKA",
                  "action" : "open", #decrease, turn_on, turn_off, open, close
                  "component" : "application", #volume, application, website
                  "value" : "кбе" #true/false - turn_off/on, application/site name, value to increase/decrease
                  } 
