import os, time, requests
from typing import Union, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from src.BasicUtils import BasicUtils

# --- Настройки ---
Prompt = Union[str, List[str]]
Response = Union[str, List[str]]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class MedicalAPI:
    """Клиент OpenRouter (облачные LLM)."""
    def __init__(self, api_key: str = None, model: str = "anthropic/claude-3-haiku"):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не найден.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "IAMOS Assistant"
        }
        BasicUtils.logger("MedicalAPI", "INFO", f"Init model: {model}")

    def generate(self, prompt: Prompt, system: str = None, temp=0.7, tokens=1024) -> Response:
        if isinstance(prompt, list):
            return [self._request(p, system, temp, tokens) for p in prompt]
        return self._request(prompt, system, temp, tokens)

    def _request(self, text: str, system: str, temp: float, tokens: int) -> str:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": text})
        
        try:
            resp = requests.post(OPENROUTER_URL, headers=self.headers, timeout=30, json={
                "model": self.model, "messages": messages, "temperature": temp, "max_tokens": tokens
            })
            resp.raise_for_status()
            res = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return res or "⚠️ Пустой ответ"
        except Exception as e:
            BasicUtils.logger("MedicalAPI", "ERROR", str(e))
            return f"❌ Ошибка API: {e}"

class LocalModel:
    """Клиент Ollama (оффлайн LLM)."""
    def __init__(self, model: str = "qwen2.5:3b", url: str = "http://localhost:11434/api/generate"):
        self.model, self.url = model, url

    def generate(self, prompt: Prompt, system: str = None, **kwargs) -> Response:
        if isinstance(prompt, list):
            return [self._request(p, system) for p in prompt]
        return self._request(prompt, system)

    def _request(self, text: str, system: str) -> str:
        full_prompt = f"{system}\n\n{text}" if system else text
        try:
            resp = requests.post(self.url, timeout=60, json={
                "model": self.model, "prompt": full_prompt, "stream": False
            })
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return f"⚠️ Ollama Error: {resp.status_code}"
        except Exception as e:
            return f"❌ Ошибка локальной модели: {e}"

class NetworkChecker(QThread):
    """Мониторинг интернет-соединения."""
    connection_changed = pyqtSignal(bool)

    def __init__(self, interval: int = 15):
        super().__init__()
        self.interval = interval
        self._is_online = False
        self._running = True

    def is_online(self) -> bool:
        return self._is_online

    def stop(self):
        self._running = False
        self.wait()

    def run(self):
        while self._running:
            try:
                # Проверка через быстрый запрос к Cloudflare
                requests.get("https://1.1.1.1", timeout=5)
                new_status = True
            except:
                new_status = False

            if new_status != self._is_online:
                self._is_online = new_status
                self.connection_changed.emit(new_status)
                BasicUtils.logger("NetChecker", "INFO", f"Online: {new_status}")
            time.sleep(self.interval)