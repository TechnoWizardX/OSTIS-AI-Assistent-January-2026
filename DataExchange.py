import json

class DataExchange():
    def update_chat_history(text, author):
        message = {
            "author" : author,
            "text" : text
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
        with open("chat_history.json", "w", encoding="utf-8") as file:
            history = json.load(file)
        return history