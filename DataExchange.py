import json
from datetime import datetime

class DataExchange():
    def update_chat_history(text, author):
        message = {
            "author" : author,
            "text" : text,
            "hour" : datetime.now().strftime("%H:%M"),
            "day" : datetime.now().strftime("%Y-%m-%d")
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
    
    def modify_config(data_key, theme):
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)

        config[data_key] = theme

        with open("config.json", "w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent = 4)

    def get_config():
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
        return config