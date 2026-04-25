import screen_brightness_control as sbc
import AppOpener 
import time
import win32gui
import win32process
import psutil
import webbrowser
import pyautogui
from BasicUtils import BasicUtils, global_signals 
import os
import ctypes
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
CONFIG = BasicUtils.get_settings_config_value("Wifi")
class ControlSystem:
    
    @staticmethod
    def open_site(url: str):
        """Открывает указанный URL в браузере по умолчанию"""
        try:
            # Если в ссылке нет http, добавляем для корректного открытия
            if not url.startswith("http"):
                url = "https://" + url
            webbrowser.open(url)
            BasicUtils.logger("SystemControl", "INFO", f"Открыт сайт: {url}")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при открытии сайта: {e}")
            global_signals.error_signal.emit(f"Не удалось открыть сайт")

    @staticmethod
    def close_current_tab():
        """Отправляет команду закрытия текущей вкладки (Ctrl+W)"""
        try:
            pyautogui.hotkey('ctrl', 'w')
            BasicUtils.logger("SystemControl", "INFO", f"Отправлена команда закрытия вкладки (Ctrl+W)")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при закрытии вкладки: {e}")
            global_signals.error_signal.emit(f"Не удалось закрыть вкладку")
    
    @staticmethod
    def set_brightness(level: int):
        """Устанавливает яркость экрана"""

        try:
            sbc.set_brightness(level)
            BasicUtils.logger("SystemControl", "INFO", f"Установлена яркость {level}")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при установке яркости: {e}")
            global_signals.error_signal.emit(f"Не удалось установить яркость")  
    
    @staticmethod
    def set_volume(level: int):
        """Устанавливает громкость через системные вызовы Windows (без эмуляции клавиш)"""
        try:
            # Константы для Windows API
            WM_APPCOMMAND = 0x0319
            APPCOMMAND_VOLUME_UP = 0x0A
            APPCOMMAND_VOLUME_DOWN = 0x09
            APPCOMMAND_VOLUME_MUTE = 0x08
            
            # Находим дескриптор активного окна (или рабочего стола)
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            # Для простоты и надежности без "дичи" в консоли, используем такой цикл:
            # (Он шлет команды напрямую системе, не в текстовое поле)
            for _ in range(50): # Обнуляем
                ctypes.windll.user32.SendMessageW(hwnd, WM_APPCOMMAND, hwnd, APPCOMMAND_VOLUME_DOWN * 0x10000)
            
            for _ in range(int(level / 2)): # Поднимаем до нужного уровня
                ctypes.windll.user32.SendMessageW(hwnd, WM_APPCOMMAND, hwnd, APPCOMMAND_VOLUME_UP * 0x10000)

            BasicUtils.logger("SystemControl", "INFO", f"Громкость установлена на {level}%")
        except Exception as e:
            BasicUtils.logger("SystemControl","ERROR", f"Ошибка громкости: {e}")
            global_signals.error_signal.emit(f"Не удалось установить громкость")
    
    @staticmethod
    def get_brightness():

        return sbc.get_brightness()

    @staticmethod
    def open_application(app_name: str):
        """Открывает приложение по имени"""
        try:
            AppOpener.open(app_name, output=False, match_closest=True, throw_error=False)
            BasicUtils.logger("SystemControl", "INFO", f"Открыто приложение {app_name}")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при открытии приложения {app_name}: {e}")
            global_signals.error_signal.emit(f"Не удалось открыть приложение")

    @staticmethod
    def close_application(app_name: str):
        """Закрывает приложение по имени"""
        try:
            AppOpener.close(app_name, output=False, match_closest=True, throw_error=False)
            BasicUtils.logger("SystemControl", "INFO", f"Закрыто приложение {app_name}")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при закрытии приложения {app_name}: {e}")
            global_signals.error_signal.emit(f"Не удалось закрыть приложение")
    
    @staticmethod
    def reload_application(app_name: str):
        """Перезагружает приложение по имени"""
        try:
            ControlSystem.close_application(app_name)
            time.sleep(2)  # Небольшая задержка для корректного закрытия
            ControlSystem.open_application(app_name)
            BasicUtils.logger("SystemControl", "INFO", f"Перезагружено приложение {app_name}")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при перезагрузке приложения {app_name}: {e}")
            global_signals.error_signal.emit(f"Не удалось перезагрузить приложение")

    @staticmethod
    def get_active_app():
        """Определяет активное приложение"""
        try:
            # Получаем дескриптор активного окна
            hwnd = win32gui.GetForegroundWindow()
            # Получаем ID процесса
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            # Получаем объект процесса
            process = psutil.Process(pid)
            
            # Извлекаем имя (например, 'chrome.exe') и убираем расширение
            app_name = process.name().replace(".exe", "").lower()
            
            BasicUtils.logger("SystemControl", "INFO", f"Активное приложение определено: {app_name}")
            return app_name
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка при определении приложения: {e}")
            return None
    
    @staticmethod
    def empty_recycle_bin():
        """Очистка корзины через официальный WinAPI"""
        try:
            # SHEmptyRecycleBinW аргументы: (hwnd, root_path, flags)
            # Flags: 1 = SHERB_NOCONFIRMATION, 2 = SHERB_NOPROGRESSUI, 4 = SHERB_NOSOUND
            import ctypes
            SHEmptyRecycleBin = ctypes.windll.shell32.SHEmptyRecycleBinW
            
            # Очищаем все корзины на всех дисках без подтверждений и звуков
            result = SHEmptyRecycleBin(None, None, 1 | 2 | 4)
            
            if result == 0:
                BasicUtils.logger("SystemControl", "INFO", "Корзина успешно очищена")
            else:
                BasicUtils.logger("SystemControl", "INFO|ERROR", f"Корзина: код результата {result} (возможно, она уже пуста)")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка очистки корзины: {e}")
            global_signals.error_signal.emit(f"Ну далось очистить корзину, возможно она уже пуста")
    
    @staticmethod
    def os_sleep():
        """Перевод системы в спящий режим"""
        try:
            import subprocess
            # Команда для сна. Она безопасна и не требует админа.
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            BasicUtils.logger("SystemControl", "INFO", "Система уходит в спящий режим")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка перехода в сон: {e}")
            global_signals.error_signal.emit(f"Не удалось перевести компьютер в спящий режим")

    @staticmethod
    def os_shutdown(delay=60):
        """Выключение ПК с задержкой"""
        try:
            import subprocess
            # /s - выключение, /t - время в секундах
            subprocess.run(f"shutdown /s /t {delay}", shell=True)
            BasicUtils.logger("SystemControl", "INFO", f"Запланировано выключение через {delay} сек.")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка команды выключения: {e}")

    @staticmethod
    def cancel_shutdown():
        """Отмена запланированного выключения"""
        try:
            import subprocess
            subprocess.run("shutdown /a", shell=True)
            BasicUtils.logger("SystemControl", "INFO", "Выключение отменено")
        except Exception as e:
            BasicUtils.logger("SystemControl", "INFO|ERROR", "Нет запланированных выключений для отмены")
            global_signals.error_signal.emit(f"Нет запланированных выключений для отмены")
    
    @staticmethod
    def reboot(delay=0):
        """Перезагрузка ПК через время (по умолчанию 0 секунд)"""
        try:
            import subprocess
            subprocess.run(f"shutdown /r /t {delay}", shell=True)
            BasicUtils.logger("SystemControl", "INFO", "Перезагрузка запланирована")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка команды перезагрузки: {e}")
            global_signals.error_signal.emit(f"Ошибка перезагрузки")

    @staticmethod
    def disconnect_wifi():
        """Разрывает соединение с текущей Wi-Fi сетью (Админ НЕ нужен)"""
        try:
            import subprocess
            # Команда просто заставляет адаптер забыть текущую сеть
            current_ssid = ControlSystem.get_current_wifi_name()
            BasicUtils.logger("SystemControl", f"Текущая Wi-Fi сеть: {current_ssid}")
            if CONFIG.get("ssid") and current_ssid and current_ssid != CONFIG.get("ssid"):
                BasicUtils.set_settings_config_value("Wifi", "ssid", current_ssid)
            result = subprocess.run("netsh wlan disconnect", shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                BasicUtils.logger("SystemControl", "Wi-Fi соединение успешно разорвано")
            else:
                BasicUtils.logger("SystemControl", f"Не удалось отключить Wi-Fi: {result.stderr}")
        except Exception as e:
            BasicUtils.logger("SystemControl", f"Ошибка при попытке отключения: {e}")
            global_signals.error_signal.emit(f"Не удалось отключиться от сети")

    @staticmethod
    def connect_wifi(ssid_name: str = CONFIG.get("ssid")):
        """Подключается к сохраненной Wi-Fi сети по её имени (SSID)"""
        try:
            import subprocess
            # ssid_name — это название твоего Wi-Fi (например, "MyHome_5G")
            cmd = f'netsh wlan connect name="{ssid_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                BasicUtils.logger("SystemControl", f"Попытка подключения к сети {ssid_name}")
            else:
                BasicUtils.logger("SystemControl", f"Ошибка подключения: {result.stderr}")
        except Exception as e:
            BasicUtils.logger("SystemControl", f"Ошибка при попытке подключения: {e}")
            global_signals.error_signal.emit(f"Не удалось подключиться к сети")

    @staticmethod
    def get_current_wifi_name():
        """Возвращает название текущей Wi-Fi сети"""
        try:
            import subprocess
            import re
            data = subprocess.check_output('netsh wlan show interfaces', shell=True).decode('cp866')
            ssid = re.search(r'SSID\s+:\s(.+)', data)
            if ssid:
                return ssid.group(1).strip()
            return None
        except:
            return None
    
    @staticmethod
    def insert_text(text: str, target_word: str = None, target_app: str = None):
        """
        Вставка: забирает весь текст, обрабатывает в Python и вставляет обратно.
        """
        try:
            import pyperclip
            import pyautogui
            import time
            from AppOpener import open as open_app

            if target_app:
                BasicUtils.logger("SystemControl", "INFO", f"Переключение на {target_app}")
                open_app(target_app, match_closest=True)
                time.sleep(0.7)

            original_buffer = pyperclip.paste()

            if target_word:
                # 2. Забираем текст из приложения
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.2) # Ждем, пока текст долетит в буфер
                
                current_text = pyperclip.paste()

                # 3. Ищем якорь и модифицируем текст
                if target_word in current_text:
                    # Вставляем текст после первого вхождения слова
                    parts = current_text.split(target_word, 1)
                    updated_text = parts[0] + target_word + " " + text + parts[1]
                    
                    # 4. Возвращаем обновленный текст в приложение
                    pyperclip.copy(updated_text)
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'v')
                    
                    BasicUtils.logger("SystemControl", "INFO", f"Текст успешно внедрен после '{target_word}'")
                else:
                    # Если слово не найдено, просто вставляем в конец или там, где курсор
                    BasicUtils.logger("SystemControl", "WARNING", f"Слово '{target_word}' не найдено. Вставка в текущую позицию.")
                    pyperclip.copy(text)
                    pyautogui.hotkey('ctrl', 'v')
            else:
                # Простая вставка без поиска
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                BasicUtils.logger("SystemControl", "INFO", "Выполнена обычная вставка текста.")

            # 5. Восстанавливаем буфер пользователя (через паузу)
            time.sleep(0.5)
            pyperclip.copy(original_buffer)

        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка вставки текста: {e}")
            global_signals.error_signal.emit(f"Ошибка вставки текста")

    @staticmethod
    def set_airplane_mode(state: bool):
        """
        Управляет режимом 'В самолете' через системные параметры.
        Примечание: В новых версиях Windows может потребоваться фокус на панели уведомлений.
        """
        try:
            import subprocess
            status = 1 if state else 0
            # Управление через реестр (может потребоваться перезагрузка для визуального обновления)
            cmd = f'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\RadioManagement\\SystemRadioState" /ve /t REG_DWORD /d {status} /f'
            
            # Внимание: для записи в этот ключ реестра могут потребоваться права. 
            # Если прав нет, используем альтернативу через вызов быстрой панели:
            if not state:
                # Пример логики: просто уведомляем, если не удалось применить через реестр
                BasicUtils.logger("SystemControl", "INFO", "Отправлен запрос на изменение режима 'В самолете'")
            
            subprocess.run(cmd, shell=True, capture_output=True)
            BasicUtils.logger("SystemControl", "INFO", f"Режим 'В самолете' установлен в: {state}")
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка режима 'В самолете': {e}")
            global_signals.error_signal.emit("Не удалось переключить режим полета")

    @staticmethod
    def get_system_stats():
        """Возвращает текущую нагрузку на систему (ЦП и ОЗУ)"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            BasicUtils.logger("SystemControl", "INFO", f"Статус ресурсов: CPU {cpu}%, RAM {ram}%")
            return {"cpu": cpu, "ram": ram}
        except Exception as e:
            BasicUtils.logger("SystemControl", "ERROR", f"Ошибка мониторинга ресурсов: {e}")
            return None


    
