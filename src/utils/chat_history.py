import json, datetime
from pathlib import Path

CHAT_FILE = Path(__file__).parent / "data" / "chat_history.json"
CHAT_FILE.parent.mkdir(exist_ok=True)


def load_chat_history() -> list:
    if CHAT_FILE.exists():
        with open(CHAT_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

def format_chat_history(history_list: list, limit: int = 5) -> str:
    """Превращает список словарей в строку: 'Автор: Текст'"""
    # Берем последние сообщения, чтобы не раздувать промпт
    recent = history_list[-limit:]
    lines = []
    for msg in recent:
        author = "Пользователь" if msg['author'] == "user" else "Ассистент"
        lines.append(f"{author}: {msg['text']}")
    
    return "\n".join(lines) if lines else "История пуста"

def save_chat_history(chat_history) -> None:
    with open(CHAT_FILE, "w", encoding="utf-8") as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)

def clear_chat_history() -> None:
    """Очищает файл истории чата (сохраняет пустой список)."""
    save_chat_history([])        


def add_message(author: str, message: str):
    history = load_chat_history()
    history.append({
        "author": author,
        "text": message,
        "time": datetime.now().strftime("%H:%M"),
        "day": datetime.now().strftime("%D-%m-%Y")
    })
    save_chat_history(history)