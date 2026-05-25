from datetime import datetime
def logger(object : str, type : str = "INFO", message : str = "") -> None:
        """Логирование событий ядра
        Args:
            object (str): Объект, который вызвал событие
            type (str, optional): Тип события (INFO, WARNING, ERROR). Defaults to "INFO".
            message (str): Сообщение для логирования
        """
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{date}] [{type}] [{object}] {message}")