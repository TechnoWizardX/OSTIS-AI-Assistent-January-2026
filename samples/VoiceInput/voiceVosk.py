import os
import sys

INTERFACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'interface'))

# Добавляем интерфейс в sys.path, если его ещё нет
if INTERFACE_DIR not in sys.path:
    sys.path.insert(0, INTERFACE_DIR)

# ✅ Теперь импорты сработают из любой вложенной папки
import json, time, queue, shutil, zipfile, tempfile, threading, urllib.request
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
from PyQt6.QtCore import Qt, QTimer

from BasicUtils import BasicUtils, global_signals  # ← Найдётся без ошибок


class VoskRecognizer:
    """
    Распознаватель речи на базе Vosk с автозагрузкой модели.
    Интерфейс 1:1 с WhisperRecognition для seamless-интеграции в AssistentCore.
    """
    
    # Константы модели (как в оригинале)
    MODEL_NAME = "vosk-model-small-ru-0.22"
    MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
    
    def __init__(self, model_path: str = None, sample_rate: int = 16000, auto_replace_numbers: bool = True):
        BasicUtils.logger("Vosk", "INFO", "Инициализация VoskRecognizer")
        
        # Автоопределение пути к модели
        if model_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.model_path = os.path.join(script_dir, "voice-model", self.MODEL_NAME)
        else:
            self.model_path = model_path
            
        self.sample_rate = sample_rate
        self.auto_replace_numbers = auto_replace_numbers

        self._numbers = self._build_numbers_dict()
        self.listening_status = False
        self.thread = None
        self.model = None
        self.recognizer = None

        # 🔥 ОТЛОЖЕННАЯ загрузка: модель загрузится при первом start_recognition()
        # когда QApplication уже точно существует → покажется GUI-окно
        self._model_ready = False
        BasicUtils.logger("Vosk", "INFO", "Загрузка модели отложена до start_recognition()")

    # =========================================================
    # АВТОЗАГРУЗКА МОДЕЛИ (инкапсулирована в классе)
    # =========================================================
    
    def _ensure_model_downloaded(self) -> bool:
        """Проверяет наличие модели, при отсутствии — запускает загрузку"""
        if os.path.exists(self.model_path):
            BasicUtils.logger("Vosk", "INFO", f"Модель найдена: {self.model_path}")
            return True
            
        BasicUtils.logger("Vosk", "INFO", "Модель не найдена, начинаю загрузку...")
        try:
            # Проверяем, запущен ли QApplication (для GUI-диалога)
            from PyQt6.QtWidgets import QApplication
            if QApplication.instance() is not None:
                # Показываем GUI-диалог загрузки
                dlg = self._DownloadDialog(self.model_path, self.MODEL_URL)
                result = dlg.exec()
                return result or os.path.exists(self.model_path)
            else:
                # Консольная загрузка (fallback)
                return self._download_model_console()
        except Exception as e:
            BasicUtils.logger("Vosk", "ERROR", f"Ошибка загрузки модели: {e}")
            # Пытаемся загрузить консольно как запасной вариант
            return self._download_model_console()
    
    def _download_model_console(self) -> bool:
        """Консольная загрузка модели с обработкой прерываний"""
        model_dir = os.path.dirname(self.model_path)
        os.makedirs(model_dir, exist_ok=True)
        
        tmp_zip = os.path.join(tempfile.gettempdir(), "vosk_model.zip")
        tmp_marker = tmp_zip + ".downloading"  # Маркер незавершённой загрузки
        
        try:
            # 🗑️ Удаляем битый файл от прошлого прерывания
            if os.path.exists(tmp_marker):
                BasicUtils.logger("Vosk", "WARNING", "Найден незавершённый файл, удаляю...")
                os.remove(tmp_marker)
            if os.path.exists(tmp_zip) and not os.path.exists(tmp_marker):
                # Файл есть, но маркера нет → возможно, старая успешная загрузка
                pass
            
            # Создаём маркер начала загрузки
            with open(tmp_marker, "w") as f:
                f.write("in_progress")
            
            BasicUtils.logger("Vosk", "INFO", f"Скачивание {self.MODEL_URL}...")
            
            with urllib.request.urlopen(self.MODEL_URL, timeout=300) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024
                
                with open(tmp_zip, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total and downloaded % (1024 * 1024) == 0:  # Лог каждые 1 МБ
                            pct = int((downloaded / total) * 100)
                            BasicUtils.logger("Vosk", "INFO", f"Загружено: {pct}% ({downloaded // 1024} КБ)")
            
            # ✅ Загрузка завершена — удаляем маркер
            if os.path.exists(tmp_marker):
                os.remove(tmp_marker)
            
            # Распаковка
            BasicUtils.logger("Vosk", "INFO", "Распаковка...")
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                # Проверка целостности архива
                bad_file = zf.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Повреждён файл в архиве: {bad_file}")
                
                root_folder = zf.namelist()[0].split("/")[0]
                tmp_extract = os.path.join(tempfile.gettempdir(), "vosk_extract")
                if os.path.exists(tmp_extract):
                    shutil.rmtree(tmp_extract)
                zf.extractall(tmp_extract)
            
            src = os.path.join(tmp_extract, root_folder)
            if not os.path.exists(src) or not os.path.exists(os.path.join(src, "am", "final.mdl")):
                raise FileNotFoundError(f"Модель неполная: {src}")
            
            # Атомарное перемещение
            if os.path.exists(self.model_path):
                shutil.rmtree(self.model_path)
            shutil.move(src, self.model_path)
            
            # Очистка
            shutil.rmtree(tmp_extract, ignore_errors=True)
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)
                
            BasicUtils.logger("Vosk", "INFO", "✅ Модель успешно загружена!")
            return True
            
        except (KeyboardInterrupt, SystemExit):
            # Пользователь прервал загрузку
            BasicUtils.logger("Vosk", "WARNING", "Загрузка прервана пользователем")
            if os.path.exists(tmp_marker):
                os.remove(tmp_marker)
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)
            return False
            
        except Exception as e:
            BasicUtils.logger("Vosk", "ERROR", f"Ошибка загрузки: {e}")
            # Не удаляем tmp_zip — может пригодиться для отладки
            if os.path.exists(tmp_marker):
                os.remove(tmp_marker)
            return False
    class _DownloadDialog:
        """Внутренний класс: окно загрузки модели в стиле основного UI"""
        
        def __init__(self, model_path: str, model_url: str):
            self.model_path = model_path
            self.model_url = model_url
            self.complete = False
            self._download_thread = None
            self.queue = queue.Queue()
            self._last_progress = 0
            self.window = None
            self._timer = None

        def _build_ui(self):
            """Создаёт UI (вызывается в exec() когда QApplication существует)"""
            self.window = QMainWindow()
            self.window.setWindowTitle("IAMOS — Загрузка модели")
            self.window.setFixedSize(520, 280)
            self.window.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.CustomizeWindowHint |
                Qt.WindowType.WindowTitleHint
            )
            self.window.setStyleSheet("background-color: #D9D9D9;")

            central = QWidget()
            self.window.setCentralWidget(central)
            lay = QVBoxLayout(central)
            lay.setContentsMargins(20, 20, 20, 20)
            lay.setSpacing(0)

            self.card = QFrame()
            self.card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 16px; }")
            card_lay = QVBoxLayout(self.card)
            card_lay.setContentsMargins(24, 24, 24, 24)
            card_lay.setSpacing(16)

            title_lay = QHBoxLayout()
            title_lay.setSpacing(12)
            title_text = QLabel("Загрузка голосовой модели")
            title_text.setStyleSheet(
                "QLabel { color: #000000; font-size: 16px; font-family: 'Roboto'; font-weight: bold; background: transparent; }"
            )
            title_lay.addWidget(title_text)
            title_lay.addStretch()
            card_lay.addLayout(title_lay)

            desc = QLabel(
                "Модель 'vosk-model-small-ru-0.22' не найдена.\n"
                "Начинается автоматическая загрузка (~50 МБ)..."
            )
            desc.setStyleSheet(
                "QLabel { color: #666666; font-size: 13px; font-family: 'Roboto'; background: transparent; }"
            )
            desc.setWordWrap(True)
            card_lay.addWidget(desc)

            self.progress_bar = QProgressBar()
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setFixedHeight(8)
            self.progress_bar.setStyleSheet("""
                QProgressBar { background-color: #E0E0E0; border-radius: 4px; border: none; }
                QProgressBar::chunk { background-color: #4FC3F7; border-radius: 4px; }
            """)
            card_lay.addWidget(self.progress_bar)

            status_lay = QHBoxLayout()
            self.status_lbl = QLabel("Подготовка...")
            self.status_lbl.setStyleSheet(
                "QLabel { color: #888888; font-size: 12px; font-family: 'Roboto'; background: transparent; }"
            )
            status_lay.addWidget(self.status_lbl)
            status_lay.addStretch()

            self.percent_lbl = QLabel("0%")
            self.percent_lbl.setStyleSheet(
                "QLabel { color: #000000; font-size: 13px; font-family: 'Roboto'; font-weight: bold; background: transparent; }"
            )
            status_lay.addWidget(self.percent_lbl)
            card_lay.addLayout(status_lay)

            lay.addWidget(self.card)

        def _center_window(self):
            screen = self.window.screen().geometry()
            w, h = 520, 280
            x = (screen.width() - w) // 2
            y = (screen.height() - h) // 2
            self.window.move(x, y)

        def set_progress(self, value: int):
            if value < self._last_progress:
                return
            self._last_progress = value
            self.progress_bar.setValue(value)
            self.percent_lbl.setText(f"{value}%")

        def set_status(self, text: str):
            self.status_lbl.setText(text)

        def mark_complete(self):
            self.complete = True
            self.status_lbl.setText("✅ Модель успешно загружена!")
            self.status_lbl.setStyleSheet(
                "QLabel { color: #4CAF50; font-size: 12px; font-family: 'Roboto'; background: transparent; }"
            )
            self.percent_lbl.setText("100%")
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet("""
                QProgressBar { background-color: #E0E0E0; border-radius: 4px; border: none; }
                QProgressBar::chunk { background-color: #4CAF50; border-radius: 4px; }
            """)
            QTimer.singleShot(3000, lambda: self.window.close())

        def mark_error(self, text: str):
            self.status_lbl.setText(f"❌ {text}")
            self.status_lbl.setStyleSheet(
                "QLabel { color: #F44336; font-size: 12px; font-family: 'Roboto'; background: transparent; }"
            )
            self.percent_lbl.setText("Ошибка")
            self.percent_lbl.setStyleSheet(
                "QLabel { color: #F44336; font-size: 13px; font-family: 'Roboto'; font-weight: bold; background: transparent; }"
            )
            QTimer.singleShot(2000, lambda: self.window.close())

        def _download(self):
            """Скачивает и распаковывает модель"""
            try:
                self.queue.put(("status", "Загрузка началась..."))
                self.queue.put(("progress", 0))

                model_dir = os.path.dirname(self.model_path)
                os.makedirs(model_dir, exist_ok=True)

                with urllib.request.urlopen(self.model_url, timeout=300) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    chunk_size = 64 * 1024
                    tmp_zip = os.path.join(tempfile.gettempdir(), "vosk_model.zip")

                    with open(tmp_zip, "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = int((downloaded / total) * 100)
                                self.queue.put(("progress", pct))
                                self.queue.put(("status", f"Загружено: {downloaded // 1024} / {total // 1024} КБ"))

                self.queue.put(("status", "Распаковка..."))
                self.queue.put(("progress", 100))

                with zipfile.ZipFile(tmp_zip, "r") as zf:
                    root_folder = zf.namelist()[0].split("/")[0]
                    tmp_extract = os.path.join(tempfile.gettempdir(), "vosk_extract")
                    if os.path.exists(tmp_extract):
                        shutil.rmtree(tmp_extract)
                    zf.extractall(tmp_extract)

                src = os.path.join(tmp_extract, root_folder)
                if not os.path.exists(src):
                    raise FileNotFoundError(f"Модель не найдена в архиве: {src}")

                if os.path.exists(self.model_path):
                    shutil.rmtree(self.model_path)
                shutil.move(src, self.model_path)

                shutil.rmtree(tmp_extract, ignore_errors=True)
                if os.path.exists(tmp_zip):
                    os.remove(tmp_zip)

                self.queue.put(("done", True))

            except Exception as e:
                self.queue.put(("error", str(e)))

        def _poll(self):
            """Опрашивает очередь и обновляет UI"""
            try:
                while True:
                    msg_type, data = self.queue.get_nowait()
                    if msg_type == "status":
                        self.set_status(data)
                    elif msg_type == "progress":
                        self.set_progress(data)
                    elif msg_type == "done":
                        self.mark_complete()
                        self._timer.stop()
                        return
                    elif msg_type == "error":
                        self.mark_error(data)
                        self._timer.stop()
                        return
            except queue.Empty:
                pass

        def exec(self) -> bool:
            """Показывает окно и ждёт завершения"""
            from PyQt6.QtCore import QEventLoop

            self._build_ui()
            self.window.show()
            self._center_window()

            self._download_thread = threading.Thread(target=self._download, daemon=True)
            self._download_thread.start()

            self._timer = QTimer()
            self._timer.timeout.connect(self._poll)
            self._timer.start(100)

            loop = QEventLoop()

            def check_done():
                if self.complete or not self.window.isVisible():
                    loop.quit()

            check_timer = QTimer()
            check_timer.timeout.connect(check_done)
            check_timer.start(50)

            loop.exec()
            check_timer.stop()
            self._timer.stop()

            return self.complete

    # =========================================================
    # ВНУТРЕННЯЯ ЛОГИКА РАСПОЗНАВАНИЯ
    # =========================================================

    def _build_numbers_dict(self) -> dict:
        """Словарь русских чисел 0-100 для автозамены"""
        numbers = {
            "ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4,
            "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
            "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
            "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
            "восемнадцать": 18, "девятнадцать": 19,
            "двадцать": 20, "тридцать": 30, "сорок": 40,
            "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
            "восемьдесят": 80, "девяносто": 90, "сто": 100
        }
        for ten, val in [("двадцать", 20), ("тридцать", 30), ("сорок", 40),
                         ("пятьдесят", 50), ("шестьдесят", 60), ("семьдесят", 70),
                         ("восемьдесят", 80), ("девяносто", 90)]:
            for unit, u_val in list(numbers.items()):
                if 1 <= u_val <= 9:
                    numbers[f"{ten} {unit}"] = val + u_val
        return numbers

    def _replace_numbers(self, text: str) -> str:
        """Заменяет русские числа на цифры (0-100)"""
        words = text.split()
        result = []
        i = 0
        while i < len(words):
            if i + 1 < len(words):
                two = f"{words[i]} {words[i+1]}"
                if two in self._numbers:
                    result.append(str(self._numbers[two]))
                    i += 2
                    continue
            if words[i] in self._numbers:
                result.append(str(self._numbers[words[i]]))
            else:
                result.append(words[i])
            i += 1
        return " ".join(result)

    def _load_model(self):
        """Загружает модель Vosk"""
        if not os.path.exists(self.model_path):
            BasicUtils.logger("Vosk", "ERROR", f"Модель не найдена: {self.model_path}")
            return
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
            BasicUtils.logger("Vosk", "INFO", "Модель Vosk успешно загружена")
        except Exception as e:
            BasicUtils.logger("Vosk", "ERROR", f"Ошибка загрузки модели: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            BasicUtils.logger("Vosk", "WARNING", f"Audio status: {status}")

        if self.recognizer:
            # 🔧 FIX: CFFI-буфер не имеет .tobytes()
            # Преобразуем буфер в байты напрямую через buffer protocol
            audio_bytes = bytes(indata)
            
            if self.recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    self._emit_recognized_text(text)

    def _emit_recognized_text(self, text: str):
        """Обработка текста и отправка в глобальную шину сигналов"""
        processed = self._replace_numbers(text) if self.auto_replace_numbers else text
        BasicUtils.logger("Vosk", "INFO", f"Распознано: {processed}")
        # 🔥 ТОТ ЖЕ СИГНАЛ, ЧТО И У WHISPER
        global_signals.voice_message_recognized.emit(processed)

    def _recognition_loop(self):
        """Основной цикл в фоновом потоке"""
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback
            ):
                while self.listening_status:
                    time.sleep(0.01)
        except Exception as e:
            BasicUtils.logger("Vosk", "ERROR", f"Ошибка в цикле распознавания: {e}")
            self.listening_status = False

    # =========================================================
    # ПУБЛИЧНЫЙ API (1:1 с WhisperRecognition)
    # =========================================================

    def start_recognition(self):
        """Запуск фоновой записи и распознавания"""
        # 🔥 КЛЮЧЕВОЙ МОМЕНТ: загружаем модель ПРЯМО СЕЙЧАС, когда QApplication уже есть
        if not self._model_ready:
            BasicUtils.logger("Vosk", "INFO", "Выполняю загрузку модели (QApplication должен быть активен)...")
            self._ensure_model_downloaded()  # ← Теперь здесь сработает проверка QApplication.instance() и покажет окно!
            self._load_model()
            self._model_ready = True
        
        # Стандартная логика запуска
        if self.listening_status or self.model is None:
            return
        BasicUtils.logger("Vosk", "INFO", "Запуск распознавания Vosk")
        self.listening_status = True
        self.thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.thread.start()

    def stop_recognition(self):
        """Мгновенная остановка распознавания"""
        if not self.listening_status:
            return
        BasicUtils.logger("Vosk", "INFO", "Остановка распознавания Vosk")
        self.listening_status = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.thread = None