import re
import Levenshtein as levenshtein

class MessageClassifier:
    """
    Класс MessageClassifier предназначен для базовой классификации сообщений от пользователя (например, студента)
    по заранее определённым шаблонам.

    Основная задача — определить класс сообщения, извлечь при необходимости сущности и их классы,
    и вернуть результат в стандартизированной структуре.
    """

    def classify(self, message: str, message_author_class: str, message_history: list[str]) -> tuple[str, dict[str], set[str]]:
        """
        Классифицирует текстовое сообщение, исходя из его содержания и принадлежности отправителя к определённому классу.

        Параметры
        ----------
        message : str
            Текст сообщения, подлежащий анализу и классификации.
        message_author_class : str
            Класс автора сообщения (например: "concept_student").
        message_history : list[str]
            История предыдущих сообщений пользователя для контекстного анализа.

        Возвращает
        ----------
        tuple[str, dict[str], set[str]]
            Кортеж из трёх элементов:
            1. Системный идентификатор класса сообщения (например: "concept_student_message_about_greeting").
            2. Основные идентификаторы сущностей и системные идентификаторы их классов, извлечённых из сообщения
            (например: {"concept": "интеллект"}).
            3. Системные идентификаторы классов сущностей, извлечённых из контекста сообщения.
        """
        if message_author_class == "concept_student":
            # Приветственное сообщение
            msg = message.lower()

            if "привет" in msg:
                return ["concept_student_message_about_greeting", {}, {}]

            if "как дела" in msg:
                return ["concept_student_message_about_casual_greeting", {}, {}]

            if "что ты умеешь" in msg:
                return ["concept_student_message_about_searching_my_skills", {}, {}]

            if "мне нужна помощь" in msg:
                return ["concept_student_message_about_help", {}, {}]

            # Запрос об открытии приложения
            variants_open = ['Открыть', 'Открой', 'Вруби', 'Запусти', 'Заведи', 'Включи', 'Активируй']
            known_apps = ["настройки", "браузер", "проводник"]

            message_lower = message.lower()
            words = message_lower.split()

            COMMAND_THRESHOLD = 0.85
            APP_THRESHOLD = 0.85

            entity = None

            for word in words:
                if max(levenshtein.ratio(word, v.lower()) for v in variants_open) >= COMMAND_THRESHOLD:

                    idx = message_lower.find(word) + len(word)
                    candidate = message_lower[idx:].strip()


                    for app in known_apps:
                        if levenshtein.ratio(candidate, app) >= APP_THRESHOLD:
                            entity = app
                            break
                    break

            if entity:
                return ["concept_message_about_open_app",{"concept_application": entity},{}]

            # Запрос об закрытии приложения
            variants_close = ['Закрыть', 'Закрой', 'Выруби', 'Заглуши', 'Выключи', 'Деактивируй']
            known_apps = ["настройки", "браузер", "проводник"]

            message_lower = message.lower()
            words = message_lower.split()

            COMMAND_THRESHOLD = 0.90
            APP_THRESHOLD = 0.90

            entity = None

            for word in words:
                if max(levenshtein.ratio(word, v.lower()) for v in variants_close) >= COMMAND_THRESHOLD:
                    idx = message_lower.find(word) + len(word)
                    candidate = message_lower[idx:].strip()

                    for app in known_apps:
                        if levenshtein.ratio(candidate, app) >= APP_THRESHOLD:
                            entity = app
                            break
                    break

            if entity:
                return ["concept_message_about_close_app",{"concept_application": entity},{}]

             
            # Запрос на уменьшение параметра
            variants_decrease = ['уменьши', 'убавь', 'снизь', 'понизь']

            message_lower = message.strip().lower()
            parts = message_lower.split()

            COMMAND_THRESHOLD = 0.90

            if len(parts) >= 4:
                verb = parts[0]

                if max(levenshtein.ratio(verb, v) for v in variants_decrease) >= COMMAND_THRESHOLD:
                    if parts[2] == 'на' and parts[3].isdigit():
                        parametr = parts[1]
                        unit = int(parts[3])

                        return [
                            "concept_message_about_decrease",
                            {
                                "concept_parametr": parametr,
                                "concept_units": unit
                            },
                            {}
                        ]
                
            # Запрос на увеличение параметра
            variants_increase = ['увеличь', 'прибавь']

            message_lower = message.strip().lower()
            parts = message_lower.split()

            COMMAND_THRESHOLD = 0.90

            if len(parts) >= 4:
                verb = parts[0]

                if max(levenshtein.ratio(verb, v) for v in variants_increase) >= COMMAND_THRESHOLD:
                    if parts[2] == 'на' and parts[3].isdigit():
                        parametr = parts[1]
                        unit = int(parts[3])

                        return [
                            "concept_message_about_increase",
                            {
                                "concept_parametr": parametr,
                                "concept_units": unit
                            },
                            {}
                        ]    
                    
            # Запрос об деактивации кнопки
            variants_close = ['Закрыть', 'Закрой', 'Выруби', 'Заглуши', 'Выключи', 'Деактивируй']
            known_buttons = ["авиарежим", "блютуз", "вайфай", "энергосбережение"]

            message_lower = message.lower()
            words = message_lower.split()

            COMMAND_THRESHOLD = 0.95
            BUTTON_THRESHOLD = 0.80
            

            entity = None

            for word in words:
                if max(levenshtein.ratio(word, v.lower()) for v in variants_close) >= COMMAND_THRESHOLD:
                    idx = message_lower.find(word) + len(word)
                    candidate = message_lower[idx:].strip()

                    for button in known_buttons:
                        if levenshtein.ratio(candidate, button) >= BUTTON_THRESHOLD:
                            entity = button
                            break
                    break

            if entity:
                return ["concept_message_about_deactivate_but",{"concept_button": entity},{}]        

            # Запрос об активации кнопки
            variants_open = ['Открыть', 'Открой', 'Вруби', 'Запусти', 'Заведи', 'Включи', 'Активируй']
            known_buttons = ["авиарежим", "блютуз", "вайфай", "энергосбережение"]

            message_lower = message.lower()
            words = message_lower.split()

            COMMAND_THRESHOLD = 0.93
            BUTTON_THRESHOLD = 0.80

            entity = None

            for word in words:
                if max(levenshtein.ratio(word, v.lower()) for v in variants_open) >= COMMAND_THRESHOLD:
                    idx = message_lower.find(word) + len(word)
                    candidate = message_lower[idx:].strip()

                    for button in known_buttons:
                        if levenshtein.ratio(candidate, button) >= BUTTON_THRESHOLD:
                            entity = button
                            break
                    break

            if entity:
                return ["concept_message_about_activate_but",{"concept_button": entity},{}]
            
        return ["concept_error_message", {}, {}]
