from datetime import datetime
import sys

def logger(object: str, type: str = "INFO", message: str = "") -> None:
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{date}] [{type}] [{object}] {message}", file=sys.stdout)

# Принудительно переключаем stdout в UTF-8 (один раз при старте приложения)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")