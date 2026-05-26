import os
import requests
from typing import Union, List

from src.utils.logger import logger

# ---------------------------------------------------------------------------
# Типы
# ---------------------------------------------------------------------------
Prompt   = Union[str, List[str]]
Response = Union[str, List[str]]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class MedicalAPI:
    """Клиент OpenRouter (облачные LLM)."""

    def __init__(self, api_key: str = None, model: str = "anthropic/claude-3-haiku"):
        self.model   = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не найден.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "X-Title":        "IAMOS Assistant",
        }
        logger("MedicalAPI", "INFO", f"Init model: {model}")

    # ------------------------------------------------------------------
    def generate(self, prompt: Prompt, system: str = None,
                 temp: float = 0.7, tokens: int = 1024) -> Response:
        if isinstance(prompt, list):
            return [self._request(p, system, temp, tokens) for p in prompt]
        return self._request(prompt, system, temp, tokens)

    def _request(self, text: str, system: str,
                 temp: float, tokens: int) -> str:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": text})
        try:
            resp = requests.post(
                OPENROUTER_URL, headers=self.headers, timeout=30,
                json={"model": self.model, "messages": messages,
                      "temperature": temp, "max_tokens": tokens},
            )
            resp.raise_for_status()
            content = (resp.json()
                       .get("choices", [{}])[0]
                       .get("message", {})
                       .get("content", "")
                       .strip())
            return content or "⚠️ Пустой ответ"
        except Exception as e:
            logger("MedicalAPI", "ERROR", str(e))
            return f"❌ Ошибка API: {e}"


class LocalModel:
    """Клиент Ollama (оффлайн LLM)."""

    def __init__(self, model: str = "qwen2.5:3b",
                 url: str = "http://localhost:11434/api/generate"):
        self.model = model
        self.url   = url

    # ------------------------------------------------------------------
    def generate(self, prompt: Prompt, system: str = None, **kwargs) -> Response:
        if isinstance(prompt, list):
            return [self._request(p, system) for p in prompt]
        return self._request(prompt, system)

    def _request(self, text: str, system: str) -> str:
        full_prompt = f"{system}\n\n{text}" if system else text
        try:
            resp = requests.post(
                self.url, timeout=60,
                json={"model": self.model, "prompt": full_prompt, "stream": False},
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return f"⚠️ Ollama Error: {resp.status_code}"
        except Exception as e:
            return f"❌ Ошибка локальной модели: {e}"