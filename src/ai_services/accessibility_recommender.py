import os, json, hashlib, re, sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
from PyQt6.QtCore import QObject, QThread, pyqtSignal

# Настройка путей
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from src.BasicUtils import BasicUtils, DataBaseEditor
from .services import LocalModel, MedicalAPI

# Константы
CACHE_PATH = os.path.join(ROOT, "data", "accessibility_cache.json")
PROMPT_PATH = os.path.join(ROOT, "data", "recommendation_prompt.md")
METHOD_LABELS = {"voice": "Голосовой ввод", "gesture": "Жестовый ввод", "text": "Текстовый ввод", "tts": "Озвучка"}

@dataclass
class RecommendationResult:
    methods: List[str]
    user_text: str

class RecommendationParser:
    """Парсит ответ LLM (JSON или текст с метками METHODS/TEXT)."""
    @staticmethod
    def parse(raw: str) -> RecommendationResult:
        # Пытаемся найти JSON
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                m = data.get("METHODS") or data.get("methods") or ""
                t = data.get("TEXT") or data.get("text") or raw
                return RecommendationResult([x.strip() for x in m.split(",") if x.strip()], t)
            except: pass
        
        # Пытаемся найти текстовые метки
        methods, text = [], raw
        for line in raw.splitlines():
            if line.upper().startswith("METHODS:"):
                methods = [m.strip() for m in line[8:].split(",") if m.strip()]
            elif line.upper().startswith("TEXT:"):
                text = line[5:].strip()
        return RecommendationResult(methods, text)

class RecommendationCache:
    """Управление кэшем рекомендаций (TTL 2 часа)."""
    def __init__(self, path=CACHE_PATH, ttl=2):
        self.path, self.ttl = path, ttl
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f: return json.load(f)
            except: pass
        return {}

    def get(self, diag: str) -> Optional[RecommendationResult]:
        key = hashlib.sha256(diag.strip().lower().encode()).hexdigest()
        entry = self.data.get(key)
        if entry:
            expired = datetime.now() - datetime.fromisoformat(entry["ts"]) > timedelta(hours=self.ttl)
            if not expired:
                return RecommendationResult(entry["methods"], entry["text"])
        return None

    def set(self, diag: str, res: RecommendationResult, model: str):
        key = hashlib.sha256(diag.strip().lower().encode()).hexdigest()
        self.data[key] = {
            "methods": res.methods, "text": res.user_text, 
            "model": model, "ts": datetime.now().isoformat()
        }
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

class RecommendationWorker(QThread):
    """Поток для запроса к LLM."""
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, u_prompt, s_prompt, api_key, model, online):
        super().__init__()
        self.u, self.s, self.key, self.model, self.online = u_prompt, s_prompt, api_key, model, online

    def run(self):
        try:
            client = MedicalAPI(self.key, self.model) if self.online else LocalModel(self.model)
            res = client.generate(self.u, system_prompt=self.s)
            if res.startswith(("⚠️", "❌")): self.failed.emit(res)
            else: self.finished.emit(res)
        except Exception as e: self.failed.emit(str(e))

class AccessibilityRecommender(QObject):
    """Фасад для получения рекомендаций доступа."""
    recommendation_obtained = pyqtSignal(object, str)

    def __init__(self, api_key=None, online="anthropic/claude-haiku-latest", offline="qwen2.5:3b"):
        super().__init__()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.on_model, self.off_model = online, offline
        self.cache, self.db = RecommendationCache(), DataBaseEditor()
        self.worker = None

    def request_recommendation(self, user_id=0, force=False):
        # 1. Получаем диагноз из БД
        rows = self.db.get_data("Users", "dysfunctions", user_id)
        diag = str(rows[0][0]).strip() if rows and rows[0][0] else None
        
        if not diag or diag.lower() == "не указано":
            return self.recommendation_obtained.emit([], "Нарушения не указаны. Все методы доступны.")

        # 2. Проверяем кэш
        if not force:
            cached = self.cache.get(diag)
            if cached: return self.recommendation_obtained.emit(cached.methods, cached.user_text)

        # 3. Подготовка запроса
        online = bool(BasicUtils.get_settings_config_value("use_online_model") and BasicUtils.has_internet())
        model = self.on_model if online else self.off_model
        
        try:
            with open(PROMPT_PATH, encoding="utf-8") as f: sys_p = f.read()
        except: sys_p = "Ты помощник по доступности. Предложи методы ввода для: "
        
        user_p = f"Особенности здоровья: {diag}. Предложи лучшие методы взаимодействия."

        # 4. Запуск потока
        if self.worker and self.worker.isRunning(): return
        self.worker = RecommendationWorker(user_p, sys_p, self.api_key, model, online)
        
        self.worker.finished.connect(lambda raw: self._handle_success(raw, diag, model))
        self.worker.start()

    def _handle_success(self, raw, diag, model):
        res = RecommendationParser.parse(raw)
        self.cache.set(diag, res, model)
        self.recommendation_obtained.emit(res.methods, res.user_text)