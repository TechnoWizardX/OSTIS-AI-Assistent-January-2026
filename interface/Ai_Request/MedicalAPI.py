import os
import requests
from typing import Union, List

class MedicalAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("Не найден API-ключ. Установите переменную OPENROUTER_API_KEY или передайте её в конструктор.")
        
        self.base_url = "https://openrouter.ai/api/v1"

        self.model = "openrouter/free"
        
    def generate(self, prompt: Union[str, List[str]]) -> Union[str, List[str]]:
        is_list = isinstance(prompt, list)
        prompts = prompt if is_list else [prompt]
        answers = []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-iamos-project",  # Требуется OpenRouter
            "X-Title": "IAMOS Medical Assistant"
        }

        for p in prompts:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Ты — профессиональный медицинский ассистент. Отвечай чётко, структурировано и только по делу. Если запрос выходит за рамки медицины, вежливо сообщи об этом."},
                    {"role": "user", "content": p}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            }
            try:
                resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                answer = data["choices"][0]["message"]["content"].strip()
                answers.append(answer)
            except requests.exceptions.HTTPError as e:
                answers.append(f"⚠️ Ошибка API ({resp.status_code}): {resp.text}")
            except Exception as e:
                answers.append(f"❌ Ошибка соединения с облачной моделью: {str(e)}")

        return answers if is_list else answers[0]