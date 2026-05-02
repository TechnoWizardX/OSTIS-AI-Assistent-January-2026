import time
from typing import Union, List

class LocalModel:
    def __init__(self):
        # В будущем: self.client = ollama.Client(host='http://localhost:11434')
        pass

    def generate(self, prompt: Union[str, List[str]]) -> Union[str, List[str]]:
        is_list = isinstance(prompt, list)
        prompts = prompt if is_list else [prompt]
        answers = []

        for p in prompts:
            # Имитация времени инференса локальной модели
            time.sleep(1.2)
            answers.append(
                f"📦 [Локальный режим] Запрос принят: «{p[:60]}...».\n"
                f"💡 Сейчас это заглушка. Для работы оффлайн подключите Ollama: "
                f"ollama run llama3.2 и замените этот код на запрос к localhost:11434."
            )

        return answers if is_list else answers[0]