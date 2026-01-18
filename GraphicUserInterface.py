from customtkinter import *
from DataExchange import *

class GraphicUserInterface():
    def __init__(self):
        self.gui_main = CTk()
        self.gui_main.geometry("900x675+400+100")
        self.gui_main.title("AI-Ассистент")

        self.gui_main.grid_columnconfigure((1, 2), weight=1)
        self.gui_main.grid_rowconfigure((0, 1), weight=1)

        self.dialoge_box = DialogeBox(self.gui_main)
        self.message_send_box = MessageSendBox(self.gui_main)
        self.option_list_box = OptionsListBox(self.gui_main)

        self.message_send_box.grid(row = 2, column = 1, padx=(10, 10), pady=(5, 10), sticky="snew", columnspan = 2)
        self.dialoge_box.grid(row = 0, column = 1, padx=(10, 10), pady=(10, 5), sticky="snew", columnspan = 2, rowspan=2)
        self.option_list_box.grid(row = 0, column = 0, padx=(10, 5), pady=(10, 10), sticky = "snew", rowspan = 3)

    def gui_start(self):
        self.gui_main.mainloop()

class DialogeBox(CTkFrame):
    def __init__(self, master):
        super().__init__(master)
    
class MessageSendBox(CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        self.message_textbox = CTkTextbox(self, font=("Arial", 16))
        self.message_textbox.grid(row = 0, column = 0, padx = (10, 10), pady = 10, sticky = "new", columnspan = 2)

        self.send_message_button = CTkButton(self, width=40, height=40, text = "Send", command=self.send_message)
        self.send_message_button.grid(row = 1, column = 1, pady = (0, 10), padx = 10, sticky = "es")

        self.delete_chat_history = CTkButton(self, text = "Delete Chat History", command=self.delete_chat_history_command, height = 40)
        self.delete_chat_history.grid(row = 1, column = 0, pady = (0, 10), padx = 10, sticky = "ws")

    def send_message(self):
        self.textbox_text = self.message_textbox.get("0.0", "end")
        self.message_textbox.delete("0.0", "end")

        if self.textbox_text != "\n":
            DataExchange.update_chat_history(self.textbox_text, "user")

    def delete_chat_history_command(self):
        DataExchange.clear_chat_history()

class OptionsListBox(CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_rowconfigure((0, 1), weight=1)

        self.settings_button = CTkButton(self, text = "Settings")
        self.settings_button.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = "n")

        self.chat_button = CTkButton(self, text="Chat")
        self.chat_button.grid(row = 1, column = 0, padx = 10, pady = 10, sticky = "n")

    


gui = GraphicUserInterface()
gui.gui_start()