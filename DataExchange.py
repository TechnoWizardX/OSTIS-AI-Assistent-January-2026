import json
from datetime import datetime

class DataExchange():
    # функции работы с историей чата
    def update_chat_history(text, author, day, time):
        message = {
            "author" : author,
            "text" : text,
            "time" : time,
            "day" : day
        }

        with open("chat_history.json", "r", encoding="utf-8") as file:
            history = json.load(file)

        history.append(message)
        
        with open("chat_history.json", "w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=4)
    
    def clear_chat_history():
        with open("chat_history.json", "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=4)

    def get_chat_history():
        with open("chat_history.json", "r", encoding="utf-8") as file:
            history = json.load(file)
        return history
    
    # функции работы с конфигурацией
    def modify_config(data_key, new_data):
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)

        config[data_key] = new_data
        with open("config.json", "w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent = 4)

    def get_config():
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
        return config

    def get_themes():
        with open("themes.json", "r", encoding="utf-8") as file:
            return json.load(file)
    
    def save_themes(new_user_theme_config):
        with open("themes.json", "r", encoding="utf-8") as file:
            new_theme_config = json.load(file)
        new_theme_config["user"] = new_user_theme_config

        with open("themes.json", "w", encoding="utf-8") as file:
            json.dump(new_theme_config, file, ensure_ascii=False, indent=4)

    # функции работы с NIKA
    def send_to_nika(text):
        pass

    def get_text_from_nika():
        text = "Здесь будет ответ от NIKA"
        return text
    
    def get_data_from_nika():
        # здесь будут поулчаться данные от nika
        pass
