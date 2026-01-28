from customtkinter import *
from DataExchange import *
from datetime import datetime
import tkinter.messagebox as messagebox
import tkinter.colorchooser as colorchooser
import tkinter.filedialog as filedialog
from VoiceRecognizer import VoiceRecognizer
from threading import Thread



class GraphicUserInterface():
    def __init__(self):
        self.theme_config = DataExchanger.get_themes()["user"]

        self.sc_connector = ScConnection()
        self.sc_connector.connect_to_sc_server()

        self.gui_main = CTk(fg_color=self.theme_config["gui_foreground"])
        self.gui_main.geometry("900x675+400+100")
        self.gui_main.title("AI-Ассистент")
        self.gui_main.minsize(620, 300)
        self.gui_main.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.gui_main.grid_columnconfigure((1, 2), weight=1)
        self.gui_main.grid_rowconfigure((0, 1), weight=1)

        # контент бокс для размещения фреймов настроек и чата
        self.content_box = CTkFrame(self.gui_main, fg_color="transparent")
        self.content_box.grid(row=0, column=1, rowspan=3, columnspan=3, sticky="nsew")

        self.content_box.grid_columnconfigure(0, weight=1)
        self.content_box.grid_rowconfigure(0, weight=1)

        #фрейм и чат боксы соответственно
        self.settings_box = SettingsBox(self.content_box)
        self.chat_box = CTkFrame(self.content_box, fg_color="transparent")
        
        #фреймы диалога и отправки сообщений внутри чат бокса
        self.dialoge_box = DialogeBox(self.chat_box)
        self.message_send_box = MessageSendBox(self.chat_box, self.dialoge_box)

        #фрейм опций слева
        self.option_list_box = OptionsListBox(self.gui_main, self, self.message_send_box)

        #размещение фреймов опций, контент бокса и чат бокса как бокс по умолчанию
        self.option_list_box.grid(row = 0, column = 0, padx=(10, 5), pady=(10, 10), sticky = "snew", rowspan = 3)
        self.content_box.grid(row=0, column=1, rowspan=3, columnspan=3, sticky="nsew", padx = 10, pady = 10)
        self.chat_box.grid(row=0, column=0, sticky="nsew")
        self.settings_box.grid(row=0, column=0, sticky="nsew")

        self.chat_box.tkraise()

        self.chat_box.grid_columnconfigure(0, weight=1)
        self.chat_box.grid_rowconfigure((0, 1), weight=1)
        # размещение диалог бокса и месседж сенд бокса внутри чат бокса
        self.dialoge_box.grid(row = 0, column = 0, pady=(0, 5), sticky="snew", columnspan = 2, rowspan=2)
        self.message_send_box.grid(row = 2, column = 0, pady=(5, 0), sticky="snew", columnspan = 2)

        self.config = DataExchanger.get_config()

        self.new_response_subscriptions = DataExchanger.subscribe_to_message(self.dialoge_box.add_message_to_box) 

        # старт GUI
    def gui_start(self):
        self.gui_main.mainloop()


        # при закрытии окна останавливаем распознавание голоса
    def on_closing(self):
        self.sc_connector.disconnect_from_sc_server()
        self.option_list_box.voice_recognizer.stop_recording()
        self.gui_main.destroy()
        # обновление конфигурации
    def update_config(self):
        self.config = DataExchanger.get_config()

    
# ===============================
# Фрейм с настройками
# ===============================

class SettingsBox(CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.theme_config = DataExchanger.get_themes()["user"]
        
        self.settings_manager_frame()
        self.theme_manager_frame()

    def settings_manager_frame(self):
        # фрейм настроек
        self.settings_frame = CTkFrame(self, fg_color=self.theme_config["other_frame"])
        self.settings_frame.grid(row=1, column=0, padx=10, pady=(5, 5), sticky = "nswe")
        # текст настроек
        self.setting_label = CTkLabel(self, text="Settings", font=("Arial", 16), fg_color=self.theme_config["other_frame"], corner_radius=5)
        self.setting_label.grid(row=0, column=0, padx=10, pady = (10, 2), sticky = "new")
        self.name_exe_pair_label = CTkLabel(self.settings_frame, fg_color=self.theme_config["button"], text="Add Name -> Exe", 
                                              font = ("Arial", 14), corner_radius=5)
        self.name_exe_pair_label.grid(row = 0, column = 0, padx=10, pady=5, sticky="we", columnspan=2)

        self.app_name_label = CTkLabel(self.settings_frame, fg_color=self.theme_config["button"], text="Name", 
                                              font = ("Arial", 14), corner_radius=5, width=75)
        self.app_name_label.grid(row = 1, column = 0, padx=10, pady=5, sticky="w")

        self.app_name_entry = CTkEntry(self.settings_frame, width=100, fg_color=self.theme_config["message_send_frame"], 
                                   font=("Arial", 14), corner_radius=5)
        self.app_name_entry.grid(row = 2, column = 0, padx=10, pady=5,sticky="w")
        
        self.app_exe_label = CTkLabel(self.settings_frame, fg_color=self.theme_config["button"], text="Exe File", 
                                              font = ("Arial", 14), corner_radius=5, width=75)
        self.app_exe_label.grid(row = 1, column = 1, padx=10, pady=5, sticky="w")

        self.app_exe_entry = CTkEntry(self.settings_frame, width=200, fg_color=self.theme_config["message_send_frame"], 
                                   font=("Arial", 14), corner_radius=5)
        self.app_exe_entry.grid(row = 2, column = 1, padx=10, pady=5,sticky="w")

        self.save_app_exe_button = CTkButton(self.settings_frame, fg_color=self.theme_config["button"], text="Add", font=("Arial", 14),
                                             corner_radius=5, 
                                             command= lambda : DataExchanger.save_name_exe_pair(self.app_name_entry.get(), self.app_exe_entry.get()))
        self.save_app_exe_button.grid(row = 3, column = 0, columnspan=2)

    def theme_manager_frame(self):
        # менджер тем
        self.theme_frame = CTkFrame(self, fg_color=self.theme_config["other_frame"])
        self.theme_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky = "nswe")
        
        self.interface_theme_manager_label = CTkLabel(self, text="Interface Theme Manager", font=("Arial", 16), 
                                                      fg_color=self.theme_config["other_frame"], corner_radius=5)
        self.interface_theme_manager_label.grid(row=2, column=0, padx=10, pady = 2, sticky = "new")

        self.load_dark_theme_button = CTkButton(self.theme_frame, text="Dark", font = ("Arial", 14), command=self.change_to_dark_theme,
                                                fg_color=self.theme_config["button"])
        self.load_light_theme_button = CTkButton(self.theme_frame, text="Light", font = ("Arial", 14), command=self.change_to_light_theme,
                                                 fg_color=self.theme_config["button"])

        self.load_dark_theme_button.grid(row=0, column=0, padx=5, pady=5, sticky="w", columnspan=2)
        self.load_light_theme_button.grid(row=0, column=2, padx=5, pady=5, sticky="w", columnspan=2)

        self.create_change_color_buttons()
        self.create_change_color_labels()
        
    def create_change_color_buttons(self):
        # кнопки для смены цветов(может быть переопределить в одну функцию)
        self.gui_frame_color_btn = CTkButton(self.theme_frame, border_width=4,
                                                  border_color="#181818", text="",
                                                  width=30, height=30, fg_color=self.theme_config["gui_foreground"],
                                                  command=lambda : self.choose_new_color(self.gui_frame_color_btn, "gui_foreground"))
        self.gui_frame_color_btn.grid(row=1, column = 0, padx=10, pady=5, sticky = "w")

        self.options_frame_color_btn = CTkButton(self.theme_frame, border_width=4,
                                                  border_color="#181818", text="",
                                                  width=30, height=30, fg_color=self.theme_config["options_frame"],
                                                  command=lambda : self.choose_new_color(self.options_frame_color_btn, "options_frame"))
        self.options_frame_color_btn.grid(row=2, column = 0, padx=10, pady=5, sticky = "w")

        self.other_frame_color_btn = CTkButton(self.theme_frame, border_width=4,
                                                  border_color="#181818", text="",
                                                  width=30, height=30, fg_color=self.theme_config["other_frame"],
                                                  command=lambda : self.choose_new_color(self.other_frame_color_btn, "other_frame"))
        self.other_frame_color_btn.grid(row=3, column = 0, padx=10, pady=5, sticky = "w")

        self.dialog_frame_color_btn = CTkButton(self.theme_frame, border_width=4,
                                                  border_color="#181818", text="",
                                                  width=30, height=30, fg_color=self.theme_config["dialog_frame"],
                                                  command=lambda : self.choose_new_color(self.dialog_frame_color_btn, "dialog_frame"))
        self.dialog_frame_color_btn.grid(row=4, column = 0, padx=10, pady=5, sticky = "w")

        self.send_message_frame_color_btn = CTkButton(self.theme_frame, border_width=4,
                                                  border_color="#181818", text="",
                                                  width=30, height=30, fg_color=self.theme_config["message_send_frame"],
                                                  command=lambda : self.choose_new_color(self.send_message_frame_color_btn, "message_send_frame"))
        self.send_message_frame_color_btn.grid(row=5, column = 0, padx=10, pady=5, sticky = "w")


        self.border_color_btn = CTkButton(self.theme_frame, border_width=4,
                                                  border_color="#181818", text="",
                                                  width=30, height=30, fg_color=self.theme_config["border_color"],
                                                  command=lambda : self.choose_new_color(self.border_color_btn, "border_color"))
        self.border_color_btn.grid(row=1, column = 2, padx=10, pady=5, sticky = "w")

        self.text_color_btn = CTkButton(self.theme_frame, border_width=4, border_color="#181818", text = "",
                                        width=30, height=30, fg_color=self.theme_config["text"],
                                        command=lambda : self.choose_new_color(self.text_color_btn, "text"))
        self.text_color_btn.grid(row=2, column=2, padx=10, pady=5, sticky="w")

        self.button_color_btn = CTkButton(self.theme_frame, border_width=4, border_color="#181818", text = "",
                                        width=30, height=30, fg_color=self.theme_config["button"],
                                        command=lambda : self.choose_new_color(self.button_color_btn, "button"))
        self.button_color_btn.grid(row=3, column=2, padx=10, pady=5, sticky="w")

        self.user_message_color_btn = CTkButton(self.theme_frame, border_width=4, border_color="#181818", text = "",
                                            width=30, height=30, fg_color=self.theme_config["user_message"],
                                            command=lambda : self.choose_new_color(self.user_message_color_btn, "user_message"))
        self.user_message_color_btn.grid(row=4, column=2, padx=10, pady=5, sticky="w")

        self.assistent_message_color_btn = CTkButton(self.theme_frame, border_width=4, border_color="#181818", text = "",
                                            width=30, height=30, fg_color=self.theme_config["assistent_message"],
                                            command=lambda : self.choose_new_color(self.assistent_message_color_btn, "assistent_message"))
        self.assistent_message_color_btn.grid(row=5, column=2, padx=10, pady=5, sticky="w")

    def create_change_color_labels(self):
        self.gui_frame_color_label = CTkLabel(self.theme_frame, text="GUI Frame Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.gui_frame_color_label.grid(row=1, column = 1, padx=10, pady=5, sticky = "w")
        
        self.options_frame_color_label = CTkLabel(self.theme_frame, text="Options Frame Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.options_frame_color_label.grid(row=2, column = 1, padx=10, pady=5, sticky = "w")

        self.other_frame_color_label = CTkLabel(self.theme_frame, text="Other Frame Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.other_frame_color_label.grid(row=3, column = 1, padx=10, pady=5, sticky = "w")

        self.dialog_frame_color_label = CTkLabel(self.theme_frame, text="Dialog Frame Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.dialog_frame_color_label.grid(row=4, column = 1, padx=10, pady=5, sticky = "w")

        self.send_message_frame_color_label = CTkLabel(self.theme_frame, text="Send Message Frame Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.send_message_frame_color_label.grid(row=5, column = 1, padx=10, pady=5, sticky = "w")


        self.border_color_label = CTkLabel(self.theme_frame, text="Border Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.border_color_label.grid(row=1, column = 3, padx=10, pady=5, sticky = "w")      

        self.text_color_label = CTkLabel(self.theme_frame, text="Text Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.text_color_label.grid(row=2, column = 3, padx=10, pady=5, sticky = "w")

        self.button_color_label = CTkLabel(self.theme_frame, text="Button Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.button_color_label.grid(row=3, column = 3, padx=10, pady=5, sticky = "w")  

        self.user_message_color_label = CTkLabel(self.theme_frame, text="User Message Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.user_message_color_label.grid(row=4, column = 3, padx=10, pady=5, sticky = "w")

        self.assistent_message_color_label = CTkLabel(self.theme_frame, text="Assistent Message Color", font=("Arial", 14),
                                                fg_color=self.theme_config["other_frame"])
        self.assistent_message_color_label.grid(row=5, column = 3, padx=10, pady=5, sticky = "w")

    def choose_new_color(self, widget, fg_key):
        try:
            color = colorchooser.askcolor()[1]
            widget.configure(fg_color=color)
            self.theme_config[fg_key] = color
            DataExchanger.save_themes(self.theme_config)
        except:
            pass

    def change_to_dark_theme(self):
        self.theme_config = DataExchanger.get_themes()["dark"]
        DataExchanger.save_themes(self.theme_config)

    def change_to_light_theme(self):
        self.theme_config = DataExchanger.get_themes()["light"]
        DataExchanger.save_themes(self.theme_config)



class DialogeBox(CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master)

        self.message_row = 0
        self.grid_columnconfigure((0, 1), weight=1)
        self.theme_config = DataExchanger.get_themes()["user"]
        self.configure(fg_color=self.theme_config["dialog_frame"])

        self.last_date = DataExchanger.get_config().get("last_message_send", "")
        self.chat_history = DataExchanger.get_chat_history()
        self.load_chat_history()
        
    def add_message_to_box(self, author, message, date, time):
        if author == "user":
            sticky_side = "e"
            fg_color = self.theme_config["user_message"]
            column = 1
        else:
            sticky_side = "w"
            column = 0
            fg_color = self.theme_config["assistent_message"]
        
        if(self.last_date != date or not self.winfo_children()):
            date_label = CTkLabel(self, text=date, font=("Arial", 14), fg_color=self.theme_config["other_frame"], corner_radius=10)
            date_label.grid(row=self.message_row, column=0, columnspan=2, pady=5)
            self.message_row += 1
            self.last_date = date
            DataExchanger.modify_config("last_message_send", date)

        message_frame = CTkFrame(self, fg_color=fg_color, corner_radius=10)
        message_frame.grid(row=self.message_row, column=column, sticky=sticky_side, padx=5, pady=2,
                           columnspan=2)
        
        message_label = CTkLabel(message_frame, text=message, font=("Arial", 16), wraplength=400, 
                                 justify="left", fg_color="transparent", bg_color="transparent")
        message_label.grid(row=0, column=0, padx=10)

        time_label = CTkLabel(message_frame, text=time, font=("Arial", 10), anchor="e", 
                              fg_color="transparent", bg_color="transparent")
        time_label.grid(row=1, column=0, padx=10, sticky="e")

        self.message_row += 1

        self.update_idletasks()
        self._parent_canvas.yview_moveto(1.0)

    def load_chat_history(self):
        for data in self.chat_history:
            author = data["author"]
            text = data["text"]
            day = data["day"]
            time = data["time"]
            self.add_message_to_box(author, text, day, time)
    
    def clear_chat_history(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.message_row = 0
        self.update_idletasks()
        self._parent_canvas.yview_moveto(0.0)



class MessageSendBox(CTkFrame):
    def __init__(self, master, dialoge_box):
        super().__init__(master)
        self.dialoge_box = dialoge_box
        self.grid_columnconfigure((0, 1), weight=1)
        self.theme_config = DataExchanger.get_themes()["user"]

        self.configure(fg_color=self.theme_config["dialog_frame"])

        self.message_textbox = CTkTextbox(self, font=("Arial", 16), fg_color=self.theme_config["message_send_frame"], 
                                          text_color="#ECECEC", height=80, corner_radius=10)
        self.message_textbox.grid(row = 0, column = 0, padx = (10, 10), pady = 10, sticky = "new", columnspan = 2)

        self.message_textbox.bind("<Return>", self.on_enter_pressed)

        self.send_message_button = CTkButton(self, width=40, height=40, text = "Send", 
                                             command=self.send_message, font=("Arial", 16),
                                             fg_color=self.theme_config["button"])
        self.send_message_button.grid(row = 1, column = 1, pady = (0, 10), padx = 10, sticky = "es")

        self.delete_chat_history = CTkButton(self, text = "Delete Chat History",  height=40,
                                             command=self.delete_chat_history_command, fg_color=self.theme_config["button"],
                                             font=("Arial", 16))
        self.delete_chat_history.grid(row = 1, column = 0, pady = (0, 10), padx = 10, sticky = "ws")

    def send_message(self):
        self.textbox_text = self.message_textbox.get("0.0", "end").rstrip('\n')
        self.message_textbox.delete("0.0", "end")

        if self.textbox_text.strip() != "":
            DataExchanger.update_chat_history(self.textbox_text, "user", datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
            self.dialoge_box.add_message_to_box("user", self.textbox_text, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
            DataExchanger.send_to_nika(self.textbox_text)

    def send_voice_message(self, text):
            DataExchanger.update_chat_history(text, "user", datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
            self.dialoge_box.add_message_to_box("user", text, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
            DataExchanger.send_to_nika(text)

    def on_enter_pressed(self, event):
        if event.state & 0x0001:  # Shift нажат
            self.message_textbox.insert("insert", "\n")
            return "break"
        else:
            self.send_message()
            return "break"

    def delete_chat_history_command(self):
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить историю чата?"):
            DataExchanger.clear_chat_history()
            self.dialoge_box.clear_chat_history()
            self.dialoge_box.update_idletasks()
            self.dialoge_box._parent_canvas.yview_moveto(1.0)



class OptionsListBox(CTkFrame):
    def __init__(self, master, gui_instance, message_send_box):
        super().__init__(master)
        self.gui_instance = gui_instance
        self.message_send_box_instance = message_send_box

        DataExchanger.modify_config("recording_enabled", False)

        self.theme_config = DataExchanger.get_themes()["user"]
        self.configure(fg_color=self.theme_config["options_frame"])
        
        self.config = DataExchanger.get_config()
        self.voice_recognizer = VoiceRecognizer()  # Инициализируем VoiceRecognizer

        self.settings_button = CTkButton(self, text = "Settings", command=self.change_to_settings, font=("Arial", 16),
                                         fg_color=self.theme_config["button"])
        self.settings_button.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = "n")

        self.chat_button = CTkButton(self, text="Chat", command=self.change_to_chat, font=("Arial", 16), 
                                     fg_color=self.theme_config["button"])
        self.chat_button.grid(row = 1, column = 0, padx = 10, pady = (0, 10), sticky = "n")

        self.recording_button = CTkButton(self, text= "Voice Enter: Off", font=("Arial", 16), command=self.recording_status_change,
                                          fg_color=self.theme_config["button"])
        self.recording_button.grid(row = 2, column = 0, padx = 10, pady = (0, 10), sticky = "n")

        self.check_errors()  # запуск проверки на ошибки
        self.check_voice_text()  # запуск проверки на текст

    def recording_status_change(self):
        self.config = DataExchanger.get_config()
        if self.config.get("recording_enabled", False):
            DataExchanger.modify_config("recording_enabled", False)
            self.recording_button.configure(text="Voice Enter: Off")
            self.voice_recognizer.stop_recording() 
        else:
            DataExchanger.modify_config("recording_enabled", True)
            self.recording_button.configure(text="Voice Enter: On")
            self.voice_recognizer.start_recording() 

    def check_errors(self):
        error = self.voice_recognizer.get_error()  
        if error:
            messagebox.showerror("Ошибка", error)  
        self.after(1000, self.check_errors) 

    def check_voice_text(self):
        text = self.voice_recognizer.get_text()  
        if text:
            self.message_send_box_instance.send_voice_message(text)
        self.after(100, self.check_voice_text) 

    def change_to_settings(self):
        self.gui_instance.settings_box.tkraise()
    
    def change_to_chat(self):
        self.gui_instance.chat_box.tkraise()


gui = GraphicUserInterface()
gui.gui_start()