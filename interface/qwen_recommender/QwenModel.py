# interface/QwenModel.py
import requests
import threading
import sys
from pathlib import Path
from tqdm import tqdm
import sys
from pathlib import Path
# Добавляем родительскую директорию в path для импорта BasicUtils
sys.path.insert(0, str(Path(__file__).parent.parent))
from BasicUtils import BasicUtils, global_signals

class QwenModel:
    """Автоматический загрузчик и менеджер модели Qwen2.5:3b (GGUF)"""
    
    def __init__(self, model_path: str = "./models/qwen2.5-3b/qwen2.5-3b.Q4_K_M.gguf"):
        self.model_file = Path(model_path)
        self.model_dir = self.model_file.parent
        self.model_url = "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
        self.min_size = 1_900_000_000  # ~1.9 GB для валидации целостности
        self._is_ready = False

        # Проверка при инициализации (как у VOSK_MODEL)
        if self._is_valid():
            self._is_ready = True
            BasicUtils.logger("QwenModel", "INFO", "Модель обнаружена и готова к использованию.")
        else:
            BasicUtils.logger("QwenModel", "WARNING", "Модель отсутствует или повреждена. Начинаю фоновую загрузку...")
            threading.Thread(target=self._download, daemon=True, name="QwenDownloader").start()

    def _is_valid(self) -> bool:
        return self.model_file.exists() and self.model_file.stat().st_size >= self.min_size

    def _download(self):
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            temp_file = self.model_file.with_suffix('.tmp')

            with requests.get(self.model_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))

                # 📊 Консольный прогресс-бар
                with tqdm(total=total, unit='B', unit_scale=True, desc="📥 Qwen2.5-3b", file=sys.stdout) as pbar:
                    with open(temp_file, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))

            if temp_file.stat().st_size < self.min_size:
                raise ValueError("Загруженный файл меньше ожидаемого размера")

            # Атомарное переименование после успешной загрузки
            temp_file.rename(self.model_file)
            self._is_ready = True
            BasicUtils.logger("QwenModel", "INFO", f"✅ Модель успешно загружена: {self.model_file}")
            
        except Exception as e:
            BasicUtils.logger("QwenModel", "ERROR", f"Ошибка загрузки модели: {e}")
            if 'temp_file' in locals() and temp_file.exists():
                temp_file.unlink(missing_ok=True)
            global_signals.error_signal.emit(f"Не удалось загрузить Qwen2.5: {e}")

    @property
    def path(self) -> str:
        """Возвращает путь к файлу модели"""
        return str(self.model_file)

    @property
    def is_ready(self) -> bool:
        """Проверка готовности модели к инференсу"""
        return self._is_ready


# =============================================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР (как VOSK_MODEL, WHISPER_MODEL)
# =============================================================================
QWEN_MODEL = QwenModel("./models/qwen2.5-3b/qwen2.5-3b.Q4_K_M.gguf")