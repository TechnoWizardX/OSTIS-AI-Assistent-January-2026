"""
AI Services — сервисные классы для работы с AI и сетью
========================================================
Объединяет:
- MedicalAPI: клиент OpenRouter API для LLM-запросов
- LocalModel: заглушка для локальных моделей (Ollama)
- NetworkChecker: проверка подключения к интернету
"""

import os
import time
from typing import Union, List, Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from BasicUtils import BasicUtils


# ============================================================================
# MedicalAPI — клиент OpenRouter API
# ============================================================================

class MedicalAPI:
    """
    Клиент для OpenRouter API (https://openrouter.ai).
    Позволяет отправлять chat-запросы к различным моделям (Gemini, Claude, GPT и др.)
    с возможностью указания системного промпта, температуры и максимального числа токенов.
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-iamos-project",
        "X-Title": "IAMOS Assistant"
    }

    def __init__(self, api_key: str = None, model: str = "anthropic/claude-3-haiku"):
        """
        :param api_key: API-ключ OpenRouter (если None, берётся из env OPENROUTER_API_KEY)
        :param model: идентификатор модели (например, "google/gemini-flash-1.5",
                      "anthropic/claude-3-haiku", "openai/gpt-4o")
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Не найден API-ключ. Установите OPENROUTER_API_KEY в .env или передайте в конструктор.")

        self.model = model
        self.headers = {**self.DEFAULT_HEADERS, "Authorization": f"Bearer {self.api_key}"}
        BasicUtils.logger("MedicalAPI", "INFO", f"Инициализация: model={model}")

    def _send_request(self, messages: list, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """
        Внутренний метод для отправки HTTP-запроса к OpenRouter.
        :param messages: список сообщений в формате [{"role": "user", "content": "..."}, ...]
        :param temperature: креативность (0.0 — детерминировано, 1.0 — разнообразно)
        :param max_tokens: максимальная длина ответа в токенах
        :return: текст ответа или сообщение об ошибке (начинается с ⚠️ или ❌)
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            BasicUtils.logger("MedicalAPI", "INFO", f"Отправка запроса к {self.model}... (temp={temperature}, max_tokens={max_tokens})")
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            result = (content or "").strip()

            if not result:
                BasicUtils.logger("MedicalAPI", "WARNING", "⚠️ API вернул пустой ответ")
            else:
                BasicUtils.logger("MedicalAPI", "INFO", f"Запрос успешно выполнен (ответ: {len(result)} символов)")

            return result

        except requests.exceptions.HTTPError as e:
            err = f"⚠️ Ошибка API ({resp.status_code}): {resp.text}"
            BasicUtils.logger("MedicalAPI", "ERROR", err)
            return err
        except Exception as e:
            err = f"❌ Ошибка сети или обработки: {str(e)}"
            BasicUtils.logger("MedicalAPI", "ERROR", err)
            return err

    def chat(self, prompt: str, system_prompt: Optional[str] = None,
             temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """
        Отправляет один запрос к модели.
        :param prompt: пользовательское сообщение
        :param system_prompt: системный промпт (задаёт роль, правила, формат ответа)
        :param temperature: температура (по умолчанию 0.7)
        :param max_tokens: максимальное количество токенов в ответе
        :return: ответ модели или сообщение об ошибке
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._send_request(messages, temperature, max_tokens)

    def batch_chat(self, prompts: List[str], system_prompt: Optional[str] = None,
                   temperature: float = 0.7, max_tokens: int = 1024) -> List[str]:
        """
        Пакетная обработка нескольких запросов (последовательно, не параллельно).
        :param prompts: список пользовательских промптов
        :return: список ответов (в том же порядке)
        """
        return [self.chat(p, system_prompt, temperature, max_tokens) for p in prompts]

    def generate(self, prompt: Union[str, List[str]], system_prompt: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 1024) -> Union[str, List[str]]:
        """
        Универсальный метод: если prompt — строка, возвращает строку;
        если список строк — возвращает список строк.
        """
        if isinstance(prompt, list):
            return self.batch_chat(prompt, system_prompt, temperature, max_tokens)
        return self.chat(prompt, system_prompt, temperature, max_tokens)


# ============================================================================
# LocalModel — заглушка для локальных моделей
# ============================================================================

class LocalModel:
    """
    Заглушка для локальных LLM (Ollama и аналоги).
    В будущем: реальная интеграция через ollama.Client(host='http://localhost:11434')
    """

    def __init__(self):
        BasicUtils.logger("LocalModel", "INFO", "Инициализация заглушки локальной модели")
        pass

    def generate(self, prompt: Union[str, List[str]]) -> Union[str, List[str]]:
        is_list = isinstance(prompt, list)
        prompts = prompt if is_list else [prompt]
        answers = []

        BasicUtils.logger("LocalModel", "INFO", f"Запрос локальной модели (запросов: {len(prompts)})")
        for p in prompts:
            time.sleep(1.2)
            answers.append(
                f"📦 [Локальный режим] Запрос принят: «{p[:60]}...».\n"
                f"💡 Сейчас это заглушка. Для работы оффлайн подключите Ollama: "
                f"ollama run llama3.2 и замените этот код на запрос к localhost:11434."
            )

        BasicUtils.logger("LocalModel", "INFO", "Локальная модель: ответы сформированы")
        return answers if is_list else answers[0]


# ============================================================================
# NetworkChecker — проверка подключения к интернету
# ============================================================================

class NetworkChecker(QThread):
    """
    Фоновый поток для периодической проверки подключения к интернету.
    Использует Cloudflare DNS (1.1.1.1) как надёжный эндпоинт.
    """

    connection_changed = pyqtSignal(bool)

    def __init__(self, check_interval: int = 15):
        """
        :param check_interval: интервал проверки в секундах (по умолчанию 15)
        """
        super().__init__()
        self.check_interval = check_interval
        self._is_online = False
        self._running = True
        BasicUtils.logger("NetworkChecker", "INFO", f"Инициализация: интервал={check_interval}с")

    def run(self):
        BasicUtils.logger("NetworkChecker", "INFO", "Запуск проверки подключения")
        while self._running:
            try:
                requests.get("https://1.1.1.1", timeout=5, headers={"User-Agent": "IAMOS/1.0"})
                new_status = True
            except Exception:
                new_status = False

            if new_status != self._is_online:
                self._is_online = new_status
                status_str = "ONLINE" if new_status else "OFFLINE"
                BasicUtils.logger("NetworkChecker", "INFO", f"Статус подключения изменён: {status_str}")
                self.connection_changed.emit(self._is_online)

            time.sleep(self.check_interval)

    def is_online(self) -> bool:
        """Возвращает текущий статус (для синхронного вызова из ядра)"""
        return self._is_online

    def stop(self):
        BasicUtils.logger("NetworkChecker", "INFO", "Остановка проверки подключения")
        self._running = False
        self.wait()
