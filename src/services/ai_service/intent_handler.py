
import json
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv
from PySide6.QtCore import QThread, Signal

from src.utils.BasicUtils import global_signals
from src.utils.logger import logger

OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "prompts"
    / "basic_prompt.md"
)

RESERVE_PROMPT = """Ты — IAMOS, ассистент для управления ОС Windows.
Твоя задача — распознать намерение пользователя и вернуть ОДИН объект JSON без лишнего текста до или после.

Формат ответа (строго один JSON, без markdown):
{
    "message": "Краткий ответ пользователю на русском",
    "tasks": [
        {"action": "действие", "function": "имя_функции", "params": {"имя_параметра": "значение"}}
    ]
}

Правила:
- Используй ТОЛЬКО функции из списка ниже, с ТОЧНО указанными именами функций и параметров.
- Если для ответа не нужно никаких действий (приветствие, вопрос, болтовня), верни "tasks": [].
- Не выдумывай имена функций и параметров.
- Значения параметров — на латинице (названия приложений и сайтов — как в Windows/URL), кроме параметров для insert_text и create_quick_note.

ДОСТУПНЫЕ ФУНКЦИИ:

Браузер:
- open_site — открыть сайт. params: {"url": "адрес"}
- close_current_tab — закрыть текущую вкладку. params: нет

Приложения и окна:
- open_application — открыть приложение. params: {"app_name": "имя"}
- close_application — закрыть приложение. params: {"app_name": "имя"}
- reload_application — перезапустить приложение. params: {"app_name": "имя"}
- minimize_all_windows — свернуть все окна. params: нет
- toggle_always_on_top — режим «поверх всех окон». params: нет
- set_window_state — состояние окна. params: {"action": "minimize" | "maximize" | "restore"}
- set_window_transparency — прозрачность окна. params: {"alpha": 0-255}
- snap_window — прижать окно к краю. params: {"side": "left" | "right"}

Параметры системы:
- set_brightness — яркость экрана. params: {"level": 0-100}
- set_volume — громкость. params: {"level": 0-100}

Питание ПК:
- os_sleep — сон. params: нет
- os_shutdown — выключение. params: {"delay": секунды}
- os_restart — перезагрузка. params: {"delay": секунды}
- cancel_shutdown — отменить выключение/перезагрузку. params: нет

Сервисные:
- insert_text — вставить текст. params: {"text": "текст", "target_word": "слово-якорь (опц.)", "target_app": "приложение (опц.)"}
- empty_recycle_bin — очистить корзину. params: нет
- get_system_stats — загрузка CPU и RAM. params: нет
- disconnect_wifi — отключить Wi-Fi. params: нет
- connect_wifi — подключиться к Wi-Fi. params: {"ssid_name": "имя сети"}
- set_airplane_mode — режим «в самолёте». params: {"state": true | false}
- create_quick_note — создать заметку. params: {"content": "текст", "filename": "имя файла (опц.)"}
- open_directory — открыть папку. params: {"path_type": "desktop" | "downloads" | "documents"}
- take_screenshot — скриншот. params: {"name": "имя файла (опц.)"}
- media_control — управление медиа. params: {"action": "play" | "pause" | "next" | "prev"}

ПРИМЕРЫ:

Пользователь: открой тг
Ответ:
{"message": "Открываю Telegram.", "tasks": [{"action": "open", "function": "open_application", "params": {"app_name": "telegram"}}]}

Пользователь: привет
Ответ:
{"message": "Привет! Чем могу помочь?", "tasks": []}

Пользователь: выключи компьютер через час
Ответ:
{"message": "Выключение через 3600 секунд.", "tasks": [{"action": "shutdown", "function": "os_shutdown", "params": {"delay": 3600}}]}

Пользователь: сделай громкость 30
Ответ:
{"message": "Громкость установлена на 30%.", "tasks": [{"action": "set", "function": "set_volume", "params": {"level": 30}}]}
"""

class IntentHandler:
    def __init__(self, offline_model="qwen2.5:3b", api_key = None, online_model = "openrouter/auto", base_url = "https://openrouter.ai/api/v1"):
        """Инициализация обработчика намерений"""
        load_dotenv()
        self.ollama_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"
        self.offline_model = offline_model
        self.base_url = base_url
        self.online_model = online_model
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        # Клиент и модуль openai (~3 с импорта) создаются при первом онлайн-запросе.
        self._online_client = None
        self._ollama_process = None
        # None = статус неизвестен; True/False — результат проверки при старте
        self._ollama_available: bool | None = None
        self.basic_prompt = self._load_prompt()
        logger("IntentHandler", "INFO", f"Инициализирован с моделью: {self.offline_model}")

    def _get_online_client(self):
        """Возвращает OpenAI-клиент, импортируя openai только при первом запросе."""
        if self._online_client is None:
            import openai

            self._online_client = openai.OpenAI(
                api_key=self._api_key,
                base_url=self.base_url,
                timeout=30.0,
                max_retries=0,
            )
        return self._online_client
    
    def _load_prompt(self, path=PROMPT_PATH) -> str:
        path = Path(path)
        if not path.exists():
            logger(
                "IntentHandler",
                "WARNING",
                f"Файл промпта не найден, используется встроенный: {path}",
            )
            return RESERVE_PROMPT

        try:
            with path.open("r", encoding="utf-8") as f:
                prompt = f.read()
            logger("IntentHandler", "INFO", f"Промпт загружен из {path}")
            return prompt or RESERVE_PROMPT
        except OSError as e:
            logger("IntentHandler", "ERROR", f"Ошибка чтения промпта: {e}")
            return RESERVE_PROMPT
        
    
    def update_api_key(self, new_key: str):
        """Обновляет API ключ для онлайн-запросов"""
        self._api_key = new_key
        self._online_client = None
        logger("IntentHandler", "INFO", "API ключ обновлен")
    
    def build_user_data(self, name: str= "", birthday: str = "", gender: str = "", 
                        chat_history: str = "", current_app: str= "", available_apps: list = []) -> str:
        """Генерирует единую строку контекста"""
        return (
            f"ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:\n"
            f"Имя: {name}, Рождение: {birthday}, Пол: {gender}\n"
            f"Текущее окружение: {current_app}\n\n"
            f"Доступные приложения(системные названия): {available_apps}\n\n"
            f"ПОСЛЕДНИЕ СООБЩЕНИЯ:{chat_history}"
        )
    
    def send_request(self, user_text: str, user_data: str = "", use_online: bool = False) -> dict:
        """Отправляет чистый запрос в Ollama и возвращает ответ"""
        prompt = self.basic_prompt + "\n\nСообщение пользователя: " + user_text
        if user_data:
            prompt += "\n\nДанные пользователя: " + user_data
        
        if use_online:
            logger("IntentHandler", "INFO", "Отправлен онлайн-запрос")
            return self._send_online_request(prompt, self.online_model)
        else:
            logger("IntentHandler", "INFO", "Отправлен офлайн-запрос")
            return self._send_offline_request(prompt, self.offline_model )
    
    def _send_offline_request(self, prompt, model) -> dict:
        """Отправляет запрос в Ollama"""
        # Статус уже известен: не тратим время на запрос в мёртвый порт
        if self._ollama_available is False:
            logger(
                "IntentHandler",
                "WARNING",
                "Ollama недоступна — офлайн-запрос пропущен",
            )
            return {
                "message": (
                    "Офлайн-модель недоступна: установите или запустите Ollama, "
                    "либо включите облачный ИИ в настройках"
                )
            }

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
                    logger("IntentHandler", "ERROR", "Не удалось распарсить JSON")
                    return {
                        "message": (
                            "Модель вернула некорректный ответ. Попробуйте ещё раз."
                        )
                    }

            return None

        except requests.exceptions.ConnectionError:
            self._ollama_available = False
            logger(
                "IntentHandler",
                "ERROR",
                "Ollama не отвечает: не установлена или не запущена",
            )
            return {
                "message": (
                    "Офлайн-модель недоступна: установите или запустите Ollama, "
                    "либо включите облачный ИИ в настройках"
                )
            }
        except Exception as e:
            logger("IntentHandler", "ERROR", f"Непредвиденная ошибка: {e}")
            return None
    
    def _send_online_request(self, prompt, model="openrouter/auto") -> dict:
        """Отправляет запрос онлайн-модели. Один ретрай при невалидной схеме ответа."""
        raw_content = ""
        for attempt in (1, 2):
            try:
                online_model = model
                response = self._get_online_client().chat.completions.create(
                    model=online_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" }
                )
                logger("IntentHandler", "INFO", f"Онлайн-модель ответила. Модель: {online_model}")
                raw_content = response.choices[0].message.content
                data = self.parse_ai_json(raw_content)
                if data is not None:
                    global_signals.intent_recognized.emit(data)
                    return data
                logger(
                    "IntentHandler",
                    "WARNING",
                    f"Некорректная схема ответа модели (попытка {attempt}/2): {raw_content[:200]}",
                )
            except Exception as e:
                logger("IntentHandler", "ERROR", f"Online API error: {e}")
                logger("IntentHandler", "ERROR", "Проверьте API ключ и доступ к интернету")
                break

        logger("IntentHandler", "INFO", "Запускаю оффлайн модель")
        return self._send_offline_request(prompt, self.offline_model)
    
    @staticmethod
    def _validate_intent(data) -> dict | None:
        """Проверяет схему интента: message — строка, tasks — список словарей."""
        if not isinstance(data, dict):
            return None
        message = data.get("message")
        tasks = data.get("tasks", [])
        if not isinstance(message, str):
            return None
        if not isinstance(tasks, list) or not all(
            isinstance(t, dict) for t in tasks
        ):
            return None
        return data

    @staticmethod
    def parse_ai_json(raw_response) -> dict:
        """
        Пытается извлечь JSON из строки, даже если модель добавила лишний текст
        """
        try:
            return IntentHandler._validate_intent(json.loads(raw_response))
        except json.JSONDecodeError:
            # 2. Если ошибка, ищем блок кода через регулярку
            match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if match:
                try:
                    return IntentHandler._validate_intent(json.loads(match.group()))
                except (json.JSONDecodeError, ValueError):
                    return None
        return None
    
    def shutdown_ollama(self):
        """Выгружает модель и завершает только запущенный этим приложением процесс."""
        # Не делаем запрос в мёртвый порт: на недоступном Ollama это
        # занимало до 5 секунд при закрытии приложения
        if self._ollama_available is False:
            logger("CORE", "INFO", "Ollama недоступна — выгрузка модели не требуется")
        else:
            try:
                unload_payload = {
                    "model": self.offline_model,
                    "keep_alive": 0
                }
                requests.post(
                    f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate",
                    json=unload_payload,
                    timeout=5,
                )
                logger("CORE", "INFO", "Модель Ollama выгружена из памяти")
            except requests.RequestException as error:
                logger("CORE", "WARNING", f"Не удалось выгрузить Ollama: {error}")

        process = self._ollama_process
        self._ollama_process = None
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger("CORE", "WARNING", "Ollama не завершилась вовремя; принудительное завершение")
                try:
                    process.kill()
                    process.wait()
                except OSError as error:
                    logger("CORE", "ERROR", f"Ошибка принудительного завершения Ollama: {error}")
            except OSError as error:
                logger("CORE", "ERROR", f"Не удалось завершить процесс Ollama: {error}")

        online_client = self._online_client
        self._online_client = None
        if online_client is not None:
            try:
                online_client.close()
            except Exception as error:
                logger("IntentHandler", "ERROR", f"Ошибка закрытия HTTP-клиента: {error}")

    @staticmethod
    def _is_ollama_running() -> bool:
        """Проверяет, отвечает ли уже локальный сервер Ollama."""
        try:
            with socket.create_connection(
                (OLLAMA_HOST, OLLAMA_PORT), timeout=0.5
            ):
                return True
        except OSError:
            return False

    def start_ollama(self):
        """Запускает Ollama, если он не запущен и установлен."""
        if self._ollama_process is not None and self._ollama_process.poll() is None:
            return

        if self._is_ollama_running():
            self._ollama_available = True
            logger("CORE", "INFO", "Ollama уже запущена")
            return

        if shutil.which("ollama") is None:
            self._ollama_available = False
            logger(
                "CORE",
                "WARNING",
                "Ollama не установлена или недоступна в PATH — "
                "офлайн-модель недоступна",
            )
            return

        try:
            # Сервер не отвечает — стартуем свой процесс (только для Windows)
            self._ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._ollama_available = True
            logger("CORE", "INFO", "Ollama serve запущен")
        except OSError as error:
            self._ollama_available = False
            logger("CORE", "WARNING", f"Не удалось запустить Ollama: {error}")

class IntentWorker(QThread):
    # Сигнал, который передаст словарь с результатом обратно в Core
    result_ready = Signal(dict)
    error = Signal(str)

    def __init__(self, handler : IntentHandler, user_text : str, user_data="" , use_online=False):
        
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
                self.result_ready.emit(result)
            else:
                self.error.emit("Пустой ответ от ИИ")
        except Exception as e:
            self.error.emit(str(e))