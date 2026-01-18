from customtkinter import *
from DataExchange import *
from datetime import datetime
import tkinter.messagebox as messagebox



class GraphicUserInterface():
    def __init__(self):
        self.gui_main = CTk()
        self.gui_main.geometry("900x675+400+100")
        self.gui_main.title("AI-Ассистент")

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
        self.option_list_box = OptionsListBox(self.gui_main, self)

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

        self.config = DataExchange.get_config()

    def gui_start(self):
        self.gui_main.mainloop()
        
    def update_config(self):
        self.config = DataExchange.get_config()



class SettingsBox(CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure((0,1), weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.settings_frame = CTkFrame(self, fg_color="#2F2F2F")
        self.settings_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky = "nswe")

        self.theme_frame = CTkFrame(self, fg_color="#2F2F2F")
        self.theme_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky = "nswe")
        


class DialogeBox(CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master)

        self.message_row = 0
        self.grid_columnconfigure((0, 1), weight=1)

        self.last_date = DataExchange.get_config().get("last_message_send", "")
        self.chat_history = DataExchange.get_chat_history()
        self.load_chat_history()
        
    def add_message_to_box(self, author, message, date, time):
        if author == "user":
            sticky_side = "e"
            fg_color ="#1f6aa5"
            column = 1
        else:
            sticky_side = "w"
            column = 0
            fg_color = "#1f6aa5"
        
        if(self.last_date != date or not self.winfo_children()):
            date_label = CTkLabel(self, text=date, font=("Arial", 14), fg_color="#444444", corner_radius=10)
            date_label.grid(row=self.message_row, column=0, columnspan=2, pady=5)
            self.message_row += 1
            self.last_date = date
            DataExchange.modify_config("last_message_send", date)

        message_frame = CTkFrame(self, fg_color=fg_color, corner_radius=10)
        message_frame.grid(row=self.message_row, column=column, sticky=sticky_side, padx=5, pady=2)
        
        message_label = CTkLabel(message_frame, text=message, font=("Arial", 16), wraplength=500, justify="left")
        message_label.grid(row=0, column=0, padx=10)

        time_label = CTkLabel(message_frame, text=time, font=("Arial", 10), anchor="e")
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

        self.message_textbox = CTkTextbox(self, font=("Arial", 16), fg_color="#2F2F2F", text_color="#ECECEC", height=80, corner_radius=10)
        self.message_textbox.grid(row = 0, column = 0, padx = (10, 10), pady = 10, sticky = "new", columnspan = 2)

        self.message_textbox.bind("<Return>", self.on_enter_pressed)

        self.send_message_button = CTkButton(self, width=40, height=40, text = "Send", 
                                             command=self.send_message, font=("Arial", 16))
        self.send_message_button.grid(row = 1, column = 1, pady = (0, 10), padx = 10, sticky = "es")

        self.delete_chat_history = CTkButton(self, text = "Delete Chat History",  height=40,
                                             command=self.delete_chat_history_command,
                                             font=("Arial", 16))
        self.delete_chat_history.grid(row = 1, column = 0, pady = (0, 10), padx = 10, sticky = "ws")

    def send_message(self):
        self.textbox_text = self.message_textbox.get("0.0", "end").rstrip('\n')
        self.message_textbox.delete("0.0", "end")

        if self.textbox_text.strip() != "":
            DataExchange.update_chat_history(self.textbox_text, "user", datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
            self.dialoge_box.add_message_to_box("user", self.textbox_text, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
             
    def on_enter_pressed(self, event):
        if event.state & 0x0001:  # Shift нажат
            self.message_textbox.insert("insert", "\n")
            return "break"
        else:
            self.send_message()
            return "break"

    def delete_chat_history_command(self):
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить историю чата?"):
            DataExchange.clear_chat_history()
            self.dialoge_box.clear_chat_history()
            self.dialoge_box.update_idletasks()
            self.dialoge_box._parent_canvas.yview_moveto(1.0)



class OptionsListBox(CTkFrame):
    def __init__(self, master, gui_instance):
        super().__init__(master)
        self.gui_instance = gui_instance
        self.settings_button = CTkButton(self, text = "Settings", command=self.change_to_settings, font=("Arial", 16))
        self.settings_button.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = "n")

        self.chat_button = CTkButton(self, text="Chat", command=self.change_to_chat, font=("Arial", 16))
        self.chat_button.grid(row = 1, column = 0, padx = 10, pady = (0, 10), sticky = "n")

    def change_to_settings(self):
        self.gui_instance.settings_box.tkraise()
    
    def change_to_chat(self):
        self.gui_instance.chat_box.tkraise()


gui = GraphicUserInterface()
gui.gui_start()