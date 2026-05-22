from PyQt6.QtCore import QObject, pyqtSignal
class Signals(QObject):
    settings_changed = pyqtSignal(dict)
    camera_selected = pyqtSignal(str)
    microphone_selected = pyqtSignal(str)
    profile_updated = pyqtSignal() # Сигнал для передачи текста из голосового ввода
    message_sent = pyqtSignal(str, str)
    voice_input_changed = pyqtSignal(bool)
    voice_message_received = pyqtSignal(str)
    speaker_pressed = pyqtSignal(str)
    speaker_stop_all = pyqtSignal()        # сброс всех кнопок для воспроизведения
    speaker_stop_request = pyqtSignal()    # остановка воспроизведения
    speaker_finished = pyqtSignal()        # конец воспроизведения без вмешательства
    history_cleared = pyqtSignal()          # для обновления чатов после очистки
    clear_history_requested = pyqtSignal()  # запрос на очистку истории (отправляется в ядро)
    recommendation_ready = pyqtSignal(list, str)  # (список методов, текст для пользователя)
    openrouter_api_key_changed = pyqtSignal(str)  # Сигнал для изменения API ключа OpenRouter
    dysfunctions_saved = pyqtSignal()  # Сигнал о сохранении нарушений
    typing_started  = pyqtSignal()    # нейросеть начала думать
    typing_finished = pyqtSignal()    # нейросеть ответила
ui_signals = Signals()