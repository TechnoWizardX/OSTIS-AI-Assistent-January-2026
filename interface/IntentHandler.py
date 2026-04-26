import requests
import json
from BasicUtils import BasicUtils

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
        - Если названо приложение (тг, дс, рисовалка, блокнот), преобразуй его в официальное английское название в нижнем регистре (telegram, discord, paint, notepad).
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

        ### ПРИМЕЧАНИЕ: Если в твоей базе знаний нету прямого определения, лучше ответь: 'Я точно не знаю, но могу поискать в интернете' и установи action: 'open', function: 'open_site', params: {'url': 'google.com/search?q=...'}.
        
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
            BasicUtils.logger("IntentHandler", "INFO", f"Отправка запроса: {user_text}")
            
            response = requests.post(self.url, json=payload, timeout=10)
            
            if response.status_code == 200:
                # Извлекаем текст ответа из структуры Ollama
                raw_response = response.json().get('response')
                # Превращаем строку в Python-словарь
                data = json.loads(raw_response)
                return data
            else:
                BasicUtils.logger("IntentHandler", "ERROR", f"Ошибка сервера Ollama: {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            BasicUtils.logger("IntentHandler", "ERROR", "Ollama не запущена! Проверьте, что она запущена")
            return None
        except Exception as e:
            BasicUtils.logger("IntentHandler", "ERROR", f"Непредвиденная ошибка: {e}")
            return None

# Пример использования (для теста):
handler = IntentHandler()
result = handler.send_request("Что такое Satisfactory?")
print(result)