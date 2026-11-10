from PySide6.QtCore import QObject, Signal


class Signals(QObject):
    settings_changed = Signal(dict)
    camera_selected = Signal(str)
    microphone_selected = Signal(str)
    profile_updated = Signal() # Сигнал для передачи текста из голосового ввода
    message_sent = Signal(str, str)
    voice_input_changed = Signal(bool)
    voice_message_received = Signal(str)
    speaker_pressed = Signal(str)
    speaker_stop_all = Signal()        # сброс всех кнопок для воспроизведения
    speaker_stop_request = Signal()    # остановка воспроизведения
    speaker_finished = Signal()        # конец воспроизведения без вмешательства
    history_cleared = Signal()          # для обновления чатов после очистки
    clear_history_requested = Signal()  # запрос на очистку истории (отправляется в ядро)
    recommendation_ready = Signal(list, str)  # (список методов, текст для пользователя)
    recommendation_requested = Signal()  # Запрос на получение рекомендации (при сохранении нарушений)
    openrouter_api_key_changed = Signal(str)  # Сигнал для изменения API ключа OpenRouter
    dysfunctions_saved = Signal()  # Сигнал о сохранении нарушений
    typing_started  = Signal()    # нейросеть начала думать
    typing_finished = Signal()    # нейросеть ответила
ui_signals = Signals()