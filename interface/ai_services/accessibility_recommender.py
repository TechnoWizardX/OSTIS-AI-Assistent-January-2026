"""
Модуль AccessibilityRecommender
================================
Предназначен для анализа ограничений здоровья пользователя (из базы данных)
и формирования рекомендации по наиболее подходящим способам ввода/вывода информации
(голос, жесты, айтрекер, свитчи и т.д.) с использованием LLM.
Результаты кэшируются в файл interface/data/accessibility_cache.json на 2 часа,
чтобы не вызывать API при повторных запросах с теми же нарушениями.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

# Определяем корень проекта (папка interface) для корректного импорта и путей
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from BasicUtils import BasicUtils, DataBaseEditor
from .services import MedicalAPI, LocalModel


class RecommendationFormatter:
    """
    Форматирует ответ от LLM (онлайн или локальной) в единый формат.
    Извлекает методы и текст пользователя из сырого ответа.
    """
    
    @staticmethod
    def parse_response(text: str) -> tuple:
        """
        Парсит ответ LLM, извлекая методы и текст для пользователя.
        Возвращает кортеж: (список методов, текст)
        """
        import re
        import json
        methods = []
        user_text = text

        try:
            # Сначала пробуем найти JSON в ответе
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    methods_val = data.get("METHODS", data.get("methods", ""))
                    text_val = data.get("TEXT", data.get("text", data.get("recommendation", "")))
                    if methods_val:
                        methods = [m.strip() for m in methods_val.split(",") if m.strip()]
                    if text_val:
                        user_text = text_val
                    if methods:
                        return methods, user_text
                except: pass
            
            # Пробуем найти METHODS: и TEXT: в тексте
            lines = text.strip().split("\n")
            for line in lines:
                if line.startswith("METHODS:"):
                    methods_str = line.replace("METHODS:", "").strip()
                    methods = [m.strip() for m in methods_str.split(",") if m.strip()]
                elif line.startswith("TEXT:"):
                    user_text = line.replace("TEXT:", "").strip()

            # Если не удалось спарсить, используем весь текст как user_text
            if not user_text:
                user_text = text
        except Exception as e:
            BasicUtils.logger("RecommendationFormatter", "WARNING", f"Ошибка парсинга рекомендации: {e}")
            user_text = text

        return methods, user_text
    
    @staticmethod
    def format_for_profile(methods: list, user_text: str) -> str:
        """
        Форматирует рекомендацию для отображения в профиле.
        :param methods: список рекомендованных методов
        :param user_text: текст объяснения от LLM
        :return: отформатированная строка для вывода
        """
        if not methods:
            return user_text
        
        # Формируем читаемые названия методов
        method_names = {
            "voice": "Голосовой ввод",
            "gesture": "Жестовый ввод",
            "text": "Текстовый ввод",
            "tts": "Озвучка сообщений"
        }
        
        readable_methods = [method_names.get(m, m) for m in methods]
        methods_str = ", ".join(readable_methods)
        
        return f"Рекомендуемые методы ввода: {methods_str}\n\n{user_text}"


class RecommendationWorker(QThread):
    """
    Рабочий поток для выполнения запроса к LLM (MedicalAPI или LocalModel).
    Позволяет не блокировать графический интерфейс во время ожидания ответа.
    """
    finished = pyqtSignal(str)   # сигнал с успешным ответом
    error = pyqtSignal(str)      # сигнал с текстом ошибки

    def __init__(self, user_prompt: str, system_prompt: str, api_key: str, model: str, use_online: bool = True):
        super().__init__()
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.api_key = api_key
        self.model = model
        self.use_online = use_online
        BasicUtils.logger("RecommendationWorker", "INFO", f"Инициализация: model={model}, use_online={use_online}")

    def run(self):
        """Запускается в отдельном потоке, отправляет запрос и эмитит сигнал."""
        try:
            BasicUtils.logger("RecommendationWorker", "INFO", "Запуск запроса к LLM")
            if self.use_online:
                api = MedicalAPI(api_key=self.api_key, model=self.model)
                result = api.chat(
                    prompt=self.user_prompt,
                    system_prompt=self.system_prompt,
                    temperature=0.2,
                    max_tokens=300
                )
            else:
                local_model = LocalModel(model=self.model)
                full_prompt = f"{self.system_prompt}\n\n{self.user_prompt}"
                result = local_model.generate(prompt=full_prompt)
                result = self._normalize_local_response(result)

            # Если ответ начинается с эмодзи-предупреждений — считаем ошибкой
            if result.startswith(("⚠️", "❌")):
                BasicUtils.logger("RecommendationWorker", "ERROR", f"API вернул ошибку: {result[:100]}")
                self.error.emit(result)
            else:
                BasicUtils.logger("RecommendationWorker", "INFO", f"Успешный ответ от API: {result[:100]}...")
                self.finished.emit(result)
        except Exception as e:
            BasicUtils.logger("RecommendationWorker", "ERROR", f"Критическая ошибка потока: {str(e)}")
            self.error.emit(f"❌ Критическая ошибка потока: {str(e)}")
    
    def _normalize_local_response(self, raw_response: str) -> str:
        """Нормализует ответ локальной модели к формату онлайн."""
        import re
        import json
        try:
            # Сначала пробуем найти JSON в ответе
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    methods_val = data.get("METHODS", data.get("methods", ""))
                    text_val = data.get("TEXT", data.get("text", data.get("recommendation", "")))
                    if methods_val and text_val:
                        return f"METHODS: {methods_val}\nTEXT: {text_val}"
                except: pass
            
            # Пробуем найти METHODS: и TEXT: в тексте
            result_lines = raw_response.strip().split("\n")
            methods_line = text_line = None
            for line in result_lines:
                line = line.strip()
                if line.upper().startswith("METHODS:"): methods_line = line
                elif line.upper().startswith("TEXT:"): text_line = line
            if methods_line and text_line:
                return f"{methods_line}\n{text_line}"
            
            # Если нашли только METHODS
            if methods_line:
                methods = [m.strip() for m in methods_line.replace("METHODS:", "").strip().split(",") if m.strip()]
                if methods:
                    return f"METHODS: {','.join(methods)}\nTEXT: {raw_response}"
            
            return raw_response
        except Exception as e:
            BasicUtils.logger("RecommendationWorker", "WARNING", f"Ошибка нормализации: {e}")
            return raw_response

class AccessibilityRecommender(QObject):
    """
    Основной класс рекомендателя.
    - Читает dysfunctions пользователя из БД.
    - Проверяет наличие актуальной рекомендации в кэше.
    - Если кэш отсутствует или устарел (TTL = 2 часа) — вызывает LLM через рабочий поток.
    - Сохраняет новый результат в кэш.
    - Выводит рекомендацию в консоль (в реальном приложении можно перенаправить в GUI).
    """
    recommendation_obtained = pyqtSignal(object, str)  # (список методов, текст для пользователя)
    # Путь к файлу кэша: interface/data/accessibility_cache.json
    CACHE_FILE = os.path.join(PROJECT_ROOT, "data", "accessibility_cache.json")
    CACHE_TTL_HOURS = 2          # время жизни кэша в часах

    def __init__(self, api_key: str = None, 
                 online_model: str = "~anthropic/claude-haiku-latest", 
                 offline_model: str = "qwen2.5:3b"):
        """
        :param api_key: ключ OpenRouter (если None, берётся из переменной окружения)
        :param online_model: модель LLM для онлайн-режима (OpenRouter)
        :param offline_model: модель LLM для оффлайн-режима (Ollama)
        """
        super().__init__()
        BasicUtils.logger("AccessibilityRecommender", "INFO", "=== Инициализация AccessibilityRecommender ===")
        self.db = DataBaseEditor()                 # для доступа к БД
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self._api_key:
            BasicUtils.logger("AccessibilityRecommender", "ERROR", "❌ Не найден OPENROUTER_API_KEY")
            raise ValueError("❌ Не найден OPENROUTER_API_KEY. Загрузите .env или передайте ключ.")

        self.online_model = online_model
        self.offline_model = offline_model
        self._worker: Optional[RecommendationWorker] = None   # текущий рабочий поток
        self._cache: Dict = self._load_cache()                # загружаем кэш из файла
        BasicUtils.logger("AccessibilityRecommender", "INFO",
                         f"Кэш инициализирован: {len(self._cache)} записей")
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Онлайн-модель: {online_model}, оффлайн-модель: {offline_model}")

    # ---------- Управление кэшем ----------
    def _load_cache(self) -> Dict:
        """Загружает словарь кэша из JSON-файла. Если файла нет — возвращает пустой словарь."""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                BasicUtils.logger("AccessibilityRecommender", "INFO", f"Кэш загружен: {len(cache)} записей")
                return cache
            else:
                BasicUtils.logger("AccessibilityRecommender", "INFO", "Файл кэша не найден, создан пустой кэш")
        except Exception as e:
            BasicUtils.logger("AccessibilityRecommender", "WARNING", f"Ошибка чтения кэша: {e}")
        return {}

    def _save_cache(self):
        """Сохраняет текущий словарь кэша в JSON-файл, предварительно создав папку при необходимости."""
        try:
            cache_dir = os.path.dirname(self.CACHE_FILE)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            BasicUtils.logger("AccessibilityRecommender", "ERROR", f"Ошибка записи кэша: {e}")

    def _get_cache_key(self, diagnosis: str) -> str:
        """
        Преобразует строку с нарушениями в хеш-ключ (SHA256).
        Это позволяет хранить кэш для разных формулировок, не боясь спецсимволов.
        """
        normalized = diagnosis.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _check_cache(self, diagnosis: str) -> Optional[tuple]:
        """
        Проверяет наличие актуальной (не устаревшей) рекомендации в кэше.
        Возвращает кортеж (methods, user_text) или None, если кэш не подходит.
        """
        key = self._get_cache_key(diagnosis)
        if key not in self._cache:
            return None

        entry = self._cache[key]
        cached_time = datetime.fromisoformat(entry["timestamp"])

        # Сравниваем возраст записи с CACHE_TTL_HOURS
        if datetime.now() - cached_time > timedelta(hours=self.CACHE_TTL_HOURS):
            BasicUtils.logger("AccessibilityRecommender", "INFO",
                             f"Кэш устарел (TTL={self.CACHE_TTL_HOURS}ч), удаляем запись")
            del self._cache[key]
            self._save_cache()
            return None

        BasicUtils.logger("AccessibilityRecommender", "INFO", "✅ Данные успешно взяты из кэша")
        methods = entry.get("methods", [])
        user_text = entry.get("user_text", entry["recommendation"])
        return methods, user_text

    def _update_cache(self, diagnosis: str, recommendation: str, model: str):
        """Добавляет или обновляет запись в кэше и сохраняет файл."""
        key = self._get_cache_key(diagnosis)
        methods, user_text = self._parse_recommendation(recommendation)
        self._cache[key] = {
            "diagnosis": diagnosis,
            "recommendation": recommendation,
            "methods": methods,
            "user_text": user_text,
            "timestamp": datetime.now().isoformat(),
            "model": model
        }
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Кэш обновлён для диагноза: {diagnosis[:50]}...")
        self._save_cache()

    def clear_cache(self):
        """Полная очистка файла кэша (удаляет все накопленные рекомендации)."""
        self._cache.clear()
        if os.path.exists(self.CACHE_FILE):
            os.remove(self.CACHE_FILE)
        BasicUtils.logger("AccessibilityRecommender", "INFO", "Кэш полностью очищен")

    # ---------- Логика запросов ----------
    def _build_prompts(self, dysfunctions: str):
        """
        Формирует системный и пользовательский промпты для LLM.
        Системный промпт задаёт роль эксперта по доступности.
        Пользовательский промпт перечисляет разрешённые методы и правила.
        """
        system_prompt = (
            "Ты — эксперт по доступности интерфейсов. "
            "Твоя задача — предложить РЕАЛЬНО выполнимые способы ВВОДА информации. "
            "Если стандартные методы физически невозможны, предложи альтернативные каналы. "
            "Предложение невозможного метода — критическая ошибка. "
            "Отвечай кратко, строго по формату, без markdown, без эмодзи, без цифр и скобок."
        )
        user_prompt = (
            f"Пользователь имеет особенности здоровья: {dysfunctions}\n"
            "Оцени, какие способы взаимодействия с системой будут наиболее удобны и безопасны.\n"
            "Доступные методы (ВЫБИРАЙ ТОЛЬКО ИЗ ЭТОГО СПИСКА):\n"
            "- voice (Голосовой ввод Whisper — работает при особенностях/нарушениях речи)\n"
            "- gesture (Жестовый ввод — требует подвижности кистей/пальцев)\n"
            "- text (Текстовый ввод — требует моторики и зрительного контроля)\n"
            "- tts (Озвучка сообщений — только ВЫВОД информации, НЕ решает задачу ввода)\n\n"
            "ПРАВИЛА:\n"
            "- ВЫБИРАЙ ТОЛЬКО методы из списка выше. НЕ предлагай айтрекер, свитчи, нейроинтерфейс, помощь ассистента или другие технологии.\n"
            "- Если нарушения делают стандартный ввод невозможным, НЕ предлагай его — выбери альтернативу из доступных методов.\n"
            "- Озвучка помогает только воспринимать информацию, но не вводить её.\n"
            "- Если запрос не связан с медициной — вежливо откажись отвечать и НЕ ПИШИ ОТВЕТ НА НЕГО.\n\n"
            "Формат ответа (СТРОГО):\n"
            "METHODS: voice,gesture,text,tts (перечисли только рекомендуемые через запятую)\n"
            "TEXT: [1-2 предложения на русском почему эти методы рекомендуются]\n\n"
            "Пример правильного ответа:\n"
            "METHODS: voice,tts\n"
            "TEXT: Рекомендуется использовать голосовой ввод и озвучку сообщений, так как они не требуют точной моторики рук.\n\n"
            "ВАЖНО: Сначала строка METHODS, затем строка TEXT. БЕЗ ЭМОДЗИ, без скобок."
        )
        return system_prompt, user_prompt

    def _get_dysfunctions(self, user_id: int = 0) -> Optional[str]:
        """
        Извлекает из таблицы Users поле dysfunctions для заданного user_id.
        Если поле пустое или равно "не указано" — возвращает None.
        """
        try:
            res = self.db.get_data("Users", "dysfunctions", user_id)
            if res and res[0][0]:
                val = str(res[0][0]).strip()
                return val if val.lower() != "не указано" else None
        except Exception as e:
            BasicUtils.logger("AccessibilityRecommender", "ERROR", f"Ошибка чтения БД: {e}")
        return None

    def request_recommendation(self, user_id: int = 0, force_refresh: bool = False, model: str = None):
        """
        Основной публичный метод. Получает рекомендацию (из кэша или через LLM) и выводит её.

        :param user_id: ID пользователя в БД (обычно 0 для текущего)
        :param force_refresh: если True — игнорирует кэш и всегда обращается к API
        :param model: позволяет временно переопределить модель (иначе используется default_model)
        """
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"=== Запрос рекомендации: user_id={user_id}, force_refresh={force_refresh} ===")
        
        # Проверяем настройку use_online_model и наличие интернета
        use_online_model = BasicUtils.get_settings_config_value("use_online_model")
        has_internet = BasicUtils.has_internet()
        use_online = use_online_model and has_internet
        
        if use_online_model and not has_internet:
            BasicUtils.logger("AccessibilityRecommender", "WARNING", "use_online_model=true, но интернета нет — используем локальную модель")
        
        dys = self._get_dysfunctions(user_id)
        if not dys:
            BasicUtils.logger("AccessibilityRecommender", "INFO", "Нарушения не указаны в профиле. Анализ пропущен.")
            return

        # Если не принудительное обновление — пробуем взять из кэша
        if not force_refresh:
            cached_result = self._check_cache(dys)
            if cached_result:
                methods, user_text = cached_result
                BasicUtils.logger("AccessibilityRecommender", "INFO", "Использована рекомендация из кэша")
                self._on_success_cached(methods, user_text)   # выводим сохранённую рекомендацию
                return
            BasicUtils.logger("AccessibilityRecommender", "INFO", "Кэш отсутствует или устарел. Запрос к API...")
        else:
            BasicUtils.logger("AccessibilityRecommender", "INFO", "Принудительное обновление (force_refresh=True)")

        # Защита от повторного запуска, если предыдущий поток ещё не завершён
        if self._worker and self._worker.isRunning():
            BasicUtils.logger("AccessibilityRecommender", "WARNING", "Предыдущий запрос ещё выполняется")
            return

        # Подготавливаем промпты
        sys_prompt, usr_prompt = self._build_prompts(dys)
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Анализ нарушений: {dys}")

        # Выбираем модель в зависимости от режима
        if use_online:
            used_model = model if model else self.online_model
        else:
            used_model = model if model else self.offline_model
        
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Используемая модель: {used_model}, онлайн={use_online}")
        # Создаём и запускаем рабочий поток
        self._worker = RecommendationWorker(usr_prompt, sys_prompt, self._api_key, used_model, use_online=use_online)

        # Внутренний слот, который обновит кэш после успешного ответа
        def on_success_with_cache(text: str):
            self._update_cache(dys, text, used_model)
            self._on_success(text)

        self._worker.finished.connect(on_success_with_cache)
        self._worker.error.connect(self._on_error)
        BasicUtils.logger("AccessibilityRecommender", "INFO", "Запуск RecommendationWorker")
        self._worker.start()

    # ---------- Обратные вызовы ----------
    def _parse_recommendation(self, text: str):
        """
        Парсит ответ LLM, извлекая методы и текст для пользователя.
        Возвращает кортеж: (список методов, текст)
        """
        return RecommendationFormatter.parse_response(text)

    def _on_success_cached(self, methods: list, user_text: str):
        """Обработчик успешного получения рекомендации из кэша."""
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Методы: {methods}")
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Текст: {user_text[:100]}...")
        self.recommendation_obtained.emit(methods, user_text)

    def _on_success(self, text: str):
        """Обработчик успешного получения рекомендации: логирует и отправляет в UI."""
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Рекомендация: {text[:100]}...")
        methods, user_text = RecommendationFormatter.parse_response(text)
        BasicUtils.logger("AccessibilityRecommender", "INFO", f"Методы: {methods}")
        self.recommendation_obtained.emit(methods, user_text)

    def _on_error(self, err: str):
        """Обработчик ошибок: логирует ошибку."""
        BasicUtils.logger("AccessibilityRecommender", "ERROR", f"Ошибка получения рекомендации: {err}")


# -------------------------------------------------------------------
# Блок для отладки (при прямом запуске файла).
# В реальном приложении этот код не выполняется при импорте модуля.
# -------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("🔍 Тест рекомендателя (кэш включён, force_refresh=False)")
    from PyQt6.QtCore import QCoreApplication, QTimer

    app = QCoreApplication(sys.argv)
    rec = AccessibilityRecommender()

    # Патчим методы, чтобы после вывода результата приложение завершалось (только для теста)
    orig_success = rec._on_success
    orig_error = rec._on_error

    def exit_after_success(text):
        orig_success(text)
        QTimer.singleShot(0, app.quit)

    def exit_after_error(err):
        orig_error(err)
        QTimer.singleShot(0, app.quit)

    rec._on_success = exit_after_success
    rec._on_error = exit_after_error

    # Вызов с force_refresh=False – первый раз пойдёт в API, повторно возьмёт из кэша
    rec.request_recommendation(user_id=0, force_refresh=False)
    sys.exit(app.exec())
