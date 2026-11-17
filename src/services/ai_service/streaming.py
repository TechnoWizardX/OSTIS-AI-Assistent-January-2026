"""Инкрементальное извлечение текста сообщения из потокового ответа модели.

Модели отвечают одним JSON-объектом вида
``{"message": "...", "tasks": [...]}``. При потоковой генерации чат может
показывать текст по мере его генерации, не дожидаясь полного ответа.
``StreamingMessageExtractor`` принимает фрагменты сырого текста и отдаёт
новые декодированные символы поля ``message``.
"""

import re

# Начало значения поля message: `"message" : "` с любыми пробелами
_MESSAGE_KEY_RE = re.compile(r'"message"\s*:\s*"')

_SIMPLE_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}

_HEX_DIGITS = set("0123456789abcdefABCDEF")


class StreamingMessageExtractor:
    """Накапливает сырой поток JSON и декодирует строку ``message`` на лету."""

    def __init__(self):
        self._raw = ""
        self._scan_pos = 0
        self._state = "seek"  # seek -> message -> done
        self._decoded = ""
        self._published = 0
        self._pending = ""  # недописанная escape-последовательность
        self.announced = False  # был ли найден ключ message

    def feed(self, chunk: str) -> str:
        """Принимает фрагмент ответа, возвращает новые символы ``message``."""
        if not chunk or self._state == "done":
            return ""
        self._raw += chunk

        if self._state == "seek":
            match = _MESSAGE_KEY_RE.search(self._raw)
            if match is None:
                return ""
            self._scan_pos = match.end()
            self._state = "message"
            self.announced = True

        self._scan()
        part = self._decoded[self._published:]
        self._published = len(self._decoded)
        return part

    def message(self) -> str:
        """Декодированный на текущий момент текст сообщения."""
        return self._decoded

    def _scan(self):
        raw = self._raw
        pos = self._scan_pos
        length = len(raw)
        chars = []

        while pos < length:
            if self._pending:
                if self._pending == "\\":
                    char = raw[pos]
                    escape = _SIMPLE_ESCAPES.get(char)
                    if escape is not None:
                        chars.append(escape)
                        self._pending = ""
                        pos += 1
                        continue
                    if char == "u":
                        self._pending = "\\u"
                        pos += 1
                        continue
                    # Неизвестная escape-последовательность: прекращаем
                    # потоковую расшифровку; финальный парсинг всё равно
                    # выполняет parse_ai_json по полному ответу
                    self._state = "done"
                    self._pending = ""
                    break
                # \\uXXXX: копим четыре hex-символа
                needed = 4 - (len(self._pending) - 2)
                take = raw[pos:pos + needed]
                self._pending += take
                pos += len(take)
                if len(self._pending) - 2 < 4:
                    break  # фрагмент недописан, ждём следующий чанк
                code = self._pending[2:]
                if all(c in _HEX_DIGITS for c in code):
                    chars.append(chr(int(code, 16)))
                    self._pending = ""
                    continue
                self._state = "done"
                self._pending = ""
                break

            char = raw[pos]
            if char == "\\":
                self._pending = "\\"
                pos += 1
                continue
            if char == '"':
                self._state = "done"
                pos += 1
                break
            chars.append(char)
            pos += 1

        self._scan_pos = pos
        if chars:
            self._decoded += "".join(chars)
