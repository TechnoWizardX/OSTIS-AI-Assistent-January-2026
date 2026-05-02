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
from Ai_Request_Manager.MedicalAPI import MedicalAPI


class RecommendationWorker(QThread):
    """
    Рабочий поток для выполнения запроса к MedicalAPI (LLM).
    Позволяет не блокировать графический интерфейс во время ожидания ответа.
    """
    finished = pyqtSignal(str)   # сигнал с успешным ответом
    error = pyqtSignal(str)      # сигнал с текстом ошибки

    def __init__(self, user_prompt: str, system_prompt: str, api_key: str, model: str):
        super().__init__()
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.api_key = api_key
        self.model = model

    def run(self):
        """Запускается в отдельном потоке, отправляет запрос и эмитит сигнал."""
        try:
            api = MedicalAPI(api_key=self.api_key, model=self.model)
            result = api.chat(
                prompt=self.user_prompt,
                system_prompt=self.system_prompt,
                temperature=0.2,      # низкая температура для детерминированных ответов
                max_tokens=300
            )
            # Если ответ начинается с эмодзи-предупреждений — считаем ошибкой
            if result.startswith(("⚠️", "❌")):
                self.error.emit(result)
            else:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"❌ Критическая ошибка потока: {str(e)}")


class AccessibilityRecommender(QObject):
    """
    Основной класс рекомендателя.
    - Читает dysfunctions пользователя из БД.
    - Проверяет наличие актуальной рекомендации в кэше.
    - Если кэш отсутствует или устарел (TTL = 2 часа) — вызывает LLM через рабочий поток.
    - Сохраняет новый результат в кэш.
    - Выводит рекомендацию в консоль (в реальном приложении можно перенаправить в GUI).
    """
    recommendation_obtained = pyqtSignal(str)
    # Путь к файлу кэша: interface/data/accessibility_cache.json
    CACHE_FILE = os.path.join(PROJECT_ROOT, "data", "accessibility_cache.json")
    CACHE_TTL_HOURS = 2          # время жизни кэша в часах

    def __init__(self, api_key: str = None, default_model: str = "~anthropic/claude-haiku-latest"):
        """
        :param api_key: ключ OpenRouter (если None, берётся из переменной окружения)
        :param default_model: модель LLM, используемая по умолчанию
        """
        super().__init__()
        self.db = DataBaseEditor()                 # для доступа к БД
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Не найден OPENROUTER_API_KEY. Загрузите .env или передайте ключ.")

        self.default_model = default_model
        self._worker: Optional[RecommendationWorker] = None   # текущий рабочий поток
        self._cache: Dict = self._load_cache()                # загружаем кэш из файла
        BasicUtils.logger("AccessibilityRecommender", "INFO",
                         f"Кэш инициализирован: {len(self._cache)} записей")

    # ---------- Управление кэшем ----------
    def _load_cache(self) -> Dict:
        """Загружает словарь кэша из JSON-файла. Если файла нет — возвращает пустой словарь."""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            BasicUtils.logger("AccessibilityRecommender", "WARNING", f"Ошибка чтения кэша: {e}")
        return {}

    def _save_cache(self):
        """Сохраняет текущий словарь кэша в JSON-файл, предварительно создав папку при необходимости."""
        try:
            cache_dir = os.path.dirname(self.CACHE_FILE)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)   # создаём interface/data, если её нет
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

    def _check_cache(self, diagnosis: str) -> Optional[str]:
        """
        Проверяет наличие актуальной (не устаревшей) рекомендации в кэше.
        Возвращает текст рекомендации или None, если кэш не подходит.
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
            self._save_cache()          # сразу сохраняем очищенный кэш
            return None

        BasicUtils.logger("AccessibilityRecommender", "INFO", "✅ Данные успешно взяты из кэша")
        return entry["recommendation"]

    def _update_cache(self, diagnosis: str, recommendation: str, model: str):
        """Добавляет или обновляет запись в кэше и сохраняет файл."""
        key = self._get_cache_key(diagnosis)
        self._cache[key] = {
            "diagnosis": diagnosis,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat(),
            "model": model
        }
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
            "Отвечай кратко, строго по формату, без markdown."
        )
        user_prompt = (
            f"Пользователь имеет особенности здоровья: {dysfunctions}\n"
            "Оцени, какие способы взаимодействия с системой будут наиболее удобны и безопасны.\n"
            "Доступные методы:\n"
            "1. 👋 Жестовый ввод (требует подвижности кистей/пальцев)\n"
            "2. 🎙️ Голосовой ввод: Vosk (при чёткой дикции) или Whisper (при особенностях/нарушениях речи)\n"
            "3. ⌨️ Текстовый ввод (требует моторики и зрительного контроля)\n"
            "4. 🔊 Озвучка/TTS (только ВЫВОД информации, НЕ решает задачу ввода)\n"
            "5. 🔮 Альтернативы: айтрекер, переключатели (свитчи), нейроинтерфейс, помощь ассистента.\n\n"
            "ПРАВИЛА:\n"
            "- Если нарушения делают стандартный ввод невозможным, НЕ предлагай его.\n"
            "- Укажи: 'Стандартный ввод недоступен. Рекомендуется: [альтернатива]'.\n"
            "- Если запрос никак не связан с медициной вежливо откажись на него отвечать и НЕ ПИШИ ОТВЕТ НА НЕГО.\n"
            "- Озвучка помогает только воспринимать информацию, но не вводить её.\n\n"
            "Формат ответа (строго):\n"
            "Рекомендация: [методы]. [1-2 коротких предложения почему].\n"
            "Не пиши лишнего. Ответь на русском языке."
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
        dys = self._get_dysfunctions(user_id)
        if not dys:
            print("\n⚠️ Нарушения не указаны в профиле. Анализ пропущен.\n")
            return

        # Если не принудительное обновление — пробуем взять из кэша
        if not force_refresh:
            cached_result = self._check_cache(dys)
            if cached_result:
                self._on_success(cached_result)   # выводим сохранённую рекомендацию
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

        used_model = model if model else self.default_model
        # Создаём и запускаем рабочий поток
        self._worker = RecommendationWorker(usr_prompt, sys_prompt, self.api_key, used_model)

        # Внутренний слот, который обновит кэш после успешного ответа
        def on_success_with_cache(text: str):
            self._update_cache(dys, text, used_model)
            self._on_success(text)

        self._worker.finished.connect(on_success_with_cache)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # ---------- Обратные вызовы ----------
    def _on_success(self, text: str):
        """Обработчик успешного получения рекомендации: печатает в консоль и логирует."""
        print("\n" + "=" * 60)
        print("🤖 РЕКОМЕНДАЦИЯ ПО ВВОДУ/ВЫВОДУ:")
        print(text)
        print("=" * 60 + "\n")
        BasicUtils.logger("AccessibilityRecommender", "INFO", "Рекомендация успешно получена")
        self.recommendation_obtained.emit(text)

    def _on_error(self, err: str):
        """Обработчик ошибок: печатает сообщение и логирует."""
        print(f"\n❌ Ошибка получения рекомендации: {err}\n")
        BasicUtils.logger("AccessibilityRecommender", "ERROR", f"Ошибка API/сети: {err}")


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