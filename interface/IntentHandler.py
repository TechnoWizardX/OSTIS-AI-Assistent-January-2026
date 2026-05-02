import requests
import json
import re
from BasicUtils import BasicUtils, global_signals
from PyQt6.QtCore import QThread, pyqtSignal
class IntentHandler:
    def __init__(self, model_name="qwen2.5:3b"):
        """Инициализация обработчика намерений"""
        self.url = "http://localhost:11434/api/generate"
        self.model = model_name
        self.basic_prompt = """
        Ты — дружелюбный ассистент-помощник для людей с психофизическими особенностями. Твоя цель: помогать управлять операционной системой, общаясь просто, тепло и понятно.

        ### ВХОДНЫЕ ДАННЫЕ:
        Тебе будут переданы:
        1. Сообщение пользователя.
        2. Контекст: Заболевания, Возраст, Имя пользователя.
        3. Состояние системы: Активное приложение, вкладка, уровни громкости (0-100) и яркости (0-100).
        4. Список доступных функций.

        ### ТВОЙ АЛГОРИТМ:
        1. **Анализ интента**: Пойми, что хочет сделать пользователь.
        2. **Нормализация (App Normalization)**:
        - Если названо приложение (тг, дс, рисовалка, блокнот и т.д.), преобразуй его в официальное английское название в нижнем регистре (telegram, discord, paint, notepad и т.д.).
        - Если указано общее название (браузер, почта), выбери наиболее подходящее стандартное приложение (google chrome, outlook).
        3. **Расчет параметров**: 
        - Если просят "сделай громче/тише", возьми текущее значение из состояния системы и прибавь/отними 10-20 единиц (или столько, сколько просит пользователь).
        - Если просят выключить "сейчас", delay = 0.
        4. **Формирование ответа**: Сообщение ("message") должно быть коротким и поддерживающим. Обращайся к пользователю по имени, если оно указано.
        
        
        ### СТРУКТУРА ВЫХОДА (ТОЛЬКО JSON):
        {
        "message": "Текст твоего ответа пользователю",
        "action": "Тип действия (open, close, set, on, off, restart, other, answer, unknown, invalid)",
        "function": "Имя функции из списка ниже (или пустая строка)",
        "params": { "имя_параметра": "значение" },
        "info": "Доп. информация для логирования или пустая строка"
        }

        ### ДОСТУПНЫЕ ФУНКЦИИ И ИХ ТКС (Триггерный контекст):

        1. БРАУЗЕР:
        - open_site(url: str) | ТКС: Открыть сайт/ссылку.
        - close_current_tab() | ТКС: Закрыть текущую вкладку.

        2. ПРИЛОЖЕНИЯ:
        - open_application(app_name: str) | ТКС: Запустить программу.
        - close_application(app_name: str) | ТКС: Закрыть программу.
        - reload_application(app_name: str) | ТКС: Перезагрузить программу.

        3. ПАРАМЕТРЫ СИСТЕМЫ:
        - set_brightness(level: int) | ТКС: Установить яркость (0-100).
        - set_volume(level: int) | ТКС: Установить громкость (0-100).

        4. ПИТАНИЕ ПК:
        - os_sleep() | ТКС: Спящий режим.
        - os_shutdown(delay: int) | ТКС: Выключить ПК через X секунд.
        - cancel_shutdown() | ТКС: Отменить выключение.
        - reboot(delay: int) | ТКС: Перезагрузить ПК через X секунд.

        5. СЕРВИСНЫЕ:
        - insert_text(text: str, target_word: str|None, target_app: str|None) | ТКС: Вставить текст (можно указать после какого слова или в какое приложение).
        - empty_recycle_bin() | ТКС: Очистить корзину.
        - get_system_stats() | ТКС: Узнать нагрузку (ЦП, ОЗУ).

        ### ПРАВИЛА ОБРАБОТКИ ОШИБОК:
        - Если действие понятно, но функции нет -> action: "invalid", function: "".
        - Если запрос вообще не понятен -> action: "unknown", function: "".
        - Если это просто беседа -> action: "answer", function: "".

        ### ПРИМЕЧАНИЕ(1): Если в твоей базе знаний нету прямого определения, отвечай строго: 'Я точно не знаю что это, но могу поискать в интернете' и установи action: 'open', function: 'open_site', params: {'url': 'google.com/search?q=...'}.
        Пример(К примечанию): Пользователь спрашивает: "Что такое спотифай", но ты не знаешь что это. Твой ответ:
        {
        "message": "Я точно не знаю что это, но могу поискать в интернете",
        "action": "open",
        "function": "open_site",
        "params": {"url": "google.com/search?q=спотифай"},
        "info": ""
        }
       
        ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
        """
        BasicUtils.logger("IntentHandler", "INFO", f"Инициализирован с моделью: {self.model}")

    def send_request(self, user_text: str):
        """Отправляет чистый запрос в Ollama и возвращает ответ"""
        prompt = self.basic_prompt + "\n\nСообщение пользователя: " + user_text
        # Формируем полезную нагрузку (payload)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Ждем полный ответ, а не поток по буквам
            "format": "json"  # Просим Ollama сразу отдавать JSON
    
        }

        try:
            response = requests.post(self.url, json=payload, timeout=15)
            if response.status_code == 200:
                raw_response = response.json().get('response')
                
                # Используем безопасный парсинг
                data = parse_ai_json(raw_response)
                
                if data:
                    global_signals.intent_recognized.emit(data)
                    return data
                else:
                    BasicUtils.logger("IntentHandler", "ERROR", "Не удалось распарсить JSON")
                    return {"message": "Ошибка формата", "action": "error"}
            
            return None

        except requests.exceptions.ConnectionError:
            BasicUtils.logger("IntentHandler", "ERROR", "Ollama не запущена! Проверьте, что она запущена")
            return None
        except Exception as e:
            BasicUtils.logger("IntentHandler", "ERROR", f"Непредвиденная ошибка: {e}")
            return None

def parse_ai_json(raw_response) -> dict:
    """
    Пытается извлечь JSON из строки, даже если модель добавила лишний текст
    """
    try:
        # 1. Пробуем прямой парсинг (если всё идеально)
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # 2. Если ошибка, ищем блок кода через регулярку
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return None
    return None

class IntentWorker(QThread):
    # Сигнал, который передаст словарь с результатом обратно в Core
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, handler, user_text):
        super().__init__()
        self.handler = handler
        self.user_text = user_text

    def run(self):
        try:
            # Вызываем твой существующий метод send_request
            result = self.handler.send_request(self.user_text)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Пустой ответ от ИИ")
        except Exception as e:
            self.error.emit(str(e))

if __name__ == "__main__":
# Пример использования (для теста):
    handler = IntentHandler("qwen2.5:3b")
    result = handler.send_request("Открой сайт Ollama")
    print(result)