import requests
import json
import re
from BasicUtils import BasicUtils, global_signals, DataBaseEditor
from PyQt6.QtCore import QThread, pyqtSignal
import openai
import subprocess
import os
from dotenv import load_dotenv, set_key
DATABASE_EDITOR = DataBaseEditor()
class IntentHandler:
    def __init__(self, offline_model="qwen2.5:3b", api_key = None, online_model = "openrouter/auto", base_url = "https://openrouter.ai/api/v1"):
        """Инициализация обработчика намерений"""
        load_dotenv()
        self.ollama_url = "http://localhost:11434/api/generate"
        self.offline_model = offline_model
        self.base_url = base_url
        self.online_model = online_model
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.online_client = openai.OpenAI(api_key=self._api_key, base_url=self.base_url)
        
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
        "tasks": [
            {
                "action": "open" | "close" | "reload" | "set" | "insert" | "empty" | "get" | "disconnect" | "connect",
                "function": "название функции из списка доступных",
                "params": {ключ: значение, ...} # Параметры для функции (может быть пустым)
            },
            ...
        ],
        }

        ### ДОСТУПНЫЕ ФУНКЦИИ И ИХ ТКС (Триггерный контекст):

        1. БРАУЗЕР:
        - open_site(url: str) | ТКС: Открыть сайт/ссылку.
        - close_current_tab() | ТКС: Закрыть текущую вкладку.

        2. ПРИЛОЖЕНИЯ:
        - open_application(app_name: str) | ТКС: Запустить программу.
        - close_application(app_name: str) | ТКС: Закрыть программу.
        - reload_application(app_name: str) | ТКС: Перезагрузить программу.
        - minimize_all_windows() | ТКС: Свернуть все окна.
        - toggle_always_on_top() | ТКС: Включить/выключить режим "Всегда сверху" для активного приложения.
        - set_window_state(action: str | "maximize" | "minimize" | "restore" | "close") | ТКС: Изменить состояние окна (развернуть во весь экран, свернуть, восстановить, закрыть) активного приложения.
        - set_window_transparency(alpha: int) | ТКС: Установить прозрачность окна активного приложения (0-255).
        - snap_window(side: str | "left" | "right") | ТКС: Прикрепить окно активного приложения к указанной стороне экрана. По умолчанию влево

        3. ПАРАМЕТРЫ СИСТЕМЫ:
        - set_brightness(level: int) | ТКС: Установить яркость (0-100).
        - set_volume(level: int) | ТКС: Установить громкость (0-100).

        4. ПИТАНИЕ ПК:
        - os_sleep() | ТКС: Спящий режим.
        - os_shutdown(delay: int) | ТКС: Выключить ПК через X секунд.
        - cancel_shutdown() | ТКС: Отменить выключение/перезагрузку ПК
        - os_restart(delay: int) | ТКС: Перезагрузить ПК через X секунд.

        5. СЕРВИСНЫЕ:
        - insert_text(text: str, target_word: str|None, target_app: str|None) | ТКС: Вставить текст (можно указать после какого слова или в какое приложение).
        - empty_recycle_bin() | ТКС: Очистить корзину.
        - get_system_stats() | ТКС: Узнать нагрузку (ЦП, ОЗУ).
        - disconnect_wifi() | ТКС: Разорвать соединение с Wi-Fi.
        - connect_wifi(ssid_name: str) | ТКС: Подключиться к Wi-Fi.
        - set_airplane_mode(state: bool) | ТКС: Включить режим 'В самолете'.
        - create_quick_note(content: str, filename: str) | ТКС: Создать быструю заметку на рабочем столе
        - open_directory(path_type: "downloads" | "documents" | "desktop" | "pictures") | ТКС: Открыть системную папку.
        - take_screenshot(name: str = None) | ТКС: Сделать скриншот экрана и сохранить его в Снимках экрана
        - media_control(action: str | "play" | "pause" | "next" | "previous") | ТКС: Управление медиаплеером (воспроизведение, пауза, следующая/предыдущая песня).

        ### ПРАВИЛА ОБРАБОТКИ ОШИБОК:
        - Если действие понятно, но функции нет -> action: "invalid", function: "".
        - Если запрос вообще не понятен -> action: "unknown", function: "".
        - Если это просто беседа -> action: "answer", function: "".

        ### ПРИМЕЧАНИЕ: Если в твоей базе знаний нету прямого определения, или нету нужных данных в запросе, отвечай строго: 
        # 'Я точно не знаю что это, но могу поискать в интернете' и установи action: 'open', function: 'open_site', params: {'url': 'google.com/search?q=...'}.
        ### НО: если пользователь просит открыть приложение, пытайся сначала сопоставить с теми, которые присылаются в промте, если нету - переводи с учетом того, что пользователь скорее всего указал название, которое произносится также как на английском .
        Пример(К примечанию): Пользователь спрашивает: "Что такое спотифай", но ты не знаешь что это. Твой ответ:
        {
        "message": "Я точно не знаю что это, но могу поискать в интернете",
        "tasks": [
            {
            "action": "open",
            "function": "open_site",
            "params": {"url": "google.com/search?q=спотифай"},
            "info": ""
            }
        ]
        }
        """
        
        BasicUtils.logger("IntentHandler", "INFO", f"Инициализирован с моделью: {self.offline_model}")
    
    def update_api_key(self, new_key: str):
        """Обновляет API ключ для онлайн-запросов"""
        self._api_key = new_key
        self.online_client = openai.OpenAI(api_key=self._api_key, base_url=self.base_url)
        BasicUtils.logger("IntentHandler", "INFO", "API ключ обновлен")
    
    def build_user_data(self, name: str= "", birthday: str = "", gender: str = "", 
                        chat_history: str = "", current_app: str= "", available_apps: list = []) -> str:
        """Генерирует единую строку контекста"""
        return (
            f"ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:\n"
            f"Имя: {name}, Рождение: {birthday}, Пол: {gender}\n"
            f"Текущее окружение: {current_app}\n\n"
            f"Доступные приложения(системные названия): {available_apps}\n\n"
            f"ПОСЛЕДНИЕ СООБЩЕНИЯ (ИСПОЛЬЗОВАТЬ ТОЛЬКО ДЯЛ КОНТЕКСТА, ВСЕ ТВОИ ФУНКЦИИ ПЕРЕЧИСЛЕНЫ В ПРОМТЕ):{chat_history}"
        )
    
    def send_request(self, user_text: str, user_data: str = "", use_online: bool = False) -> dict:
        """Отправляет чистый запрос в Ollama и возвращает ответ"""
        prompt = self.basic_prompt + "\n\nСообщение пользователя: " + user_text
        if user_data:
            prompt += "\n\nДанные пользователя: " + user_data
        
        if use_online:
            BasicUtils.logger("IntentHandler", "INFO", "Отправлен онлайн-запрос")
            return self._send_online_request(prompt, self.online_model)
        else:
            BasicUtils.logger("IntentHandler", "INFO", "Отправлен офлайн-запрос")
            return self._send_offline_request(prompt, self.offline_model )
    
    def _send_offline_request(self, prompt, model) -> dict:
        """Отправляет запрос в Ollama"""
        payload = {
            "model": self.offline_model,
            "prompt": prompt,
            "stream": False,  # Ждем полный ответ, а не поток по буквам
            "format": "json"  # Просим Ollama сразу отдавать JSON
    
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=15)
            if response.status_code == 200:
                raw_response = response.json().get('response')
                
                # Используем безопасный парсинг
                data = IntentHandler.parse_ai_json(raw_response)
                
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
    
    def _send_online_request(self, prompt, model="openrouter/auto") -> dict:
        """Отправляет запрос онлайн-модели"""
        try:
            online_model = model
            response = self.online_client.chat.completions.create(
                model=online_model, 
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            BasicUtils.logger("IntentHandler", "INFO", f"Онлайн-модель ответила. Модель: {online_model}")
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            BasicUtils.logger("IntentHandler", "ERROR", f"Online API error: {e}")
            BasicUtils.logger("IntentHandler", "ERROR", "Проверьте API ключ и доступ к интернету")
            BasicUtils.logger("IntentHandler", "INFO", "Запускаю оффлайн модель")
            return self._send_offline_request(prompt, self.offline_model)
    
    def parse_ai_json(raw_response) -> dict:
        """
        Пытается извлечь JSON из строки, даже если модель добавила лишний текст
        """
        try:
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
    
    def shutdown_ollama(self):
        """Полная выгрузка модели из памяти"""
        try:

            unload_payload = {
                "model": self.offline_model,
                "keep_alive": 0
            }
            requests.post("http://localhost:11434/api/generate", json=unload_payload)
            BasicUtils.logger("CORE", "INFO", "Модель Ollama выгружена из памяти")
            
        except Exception as e:
            print(f"Ошибка при закрытии Ollama: {e}")

    def start_ollama(self):
        """Запускает Ollama, если он не запущен"""
        try:
            # Проверяем, запущен ли процесс, если нет - стартуем (только для Windows)
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            BasicUtils.logger("CORE", "INFO", "Ollama serve запущен")
        except: pass

class IntentWorker(QThread):
    # Сигнал, который передаст словарь с результатом обратно в Core
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, handler, user_text, user_data="", use_online=False):
        
        super().__init__()
        self.handler = handler
        self.user_text = user_text
        self.user_data = user_data
        self.use_online = use_online

    def run(self):
        try:
            # Вызываем твой существующий метод send_request
            result = self.handler.send_request(self.user_text, self.user_data, self.use_online)
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