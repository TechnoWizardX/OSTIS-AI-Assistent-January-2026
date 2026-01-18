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
        self.message_send_box = MessageSendBox(self.gui_main, self.dialoge_box)
        self.option_list_box = OptionsListBox(self.gui_main)

        self.message_send_box.grid(row = 2, column = 1, padx=(10, 10), pady=(5, 10), sticky="snew", columnspan = 2)
        self.dialoge_box.grid(row = 0, column = 1, padx=(10, 10), pady=(10, 5), sticky="snew", columnspan = 2, rowspan=2)
        self.option_list_box.grid(row = 0, column = 0, padx=(10, 5), pady=(10, 10), sticky = "snew", rowspan = 3)

        self.config = DataExchange.get_config()

    def gui_start(self):
        self.gui_main.mainloop()
        
    def update_config(self):
        self.config = DataExchange.get_config()





class DialogeBox(CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master)

        self.message_row = 0
        self.grid_columnconfigure((0, 1), weight=1)
        self.chat_history = DataExchange.get_chat_history()
        self.load_chat_history()
        
    def add_message_to_box(self, author, message):
        print(f"message{self.message_row}")
        if author == "user":
            sticky_side = "e"
            column = 1
        else:
            sticky_side = "w"
            column = 0
        
        message_frame = CTkFrame(self, fg_color="#1f6aa5", corner_radius=10)
        message_frame.grid(row=self.message_row, column=column, sticky=sticky_side, padx=5, pady=2)
        
        message_label = CTkLabel(message_frame, text=message, font=("Arial", 16), wraplength=400, justify="left")
        message_label.pack(padx=10, pady=5)

        self.message_row += 1

        self.update_idletasks()
        self._parent_canvas.yview_moveto(1.0)

    def load_chat_history(self):
        for data in self.chat_history:
            author = data["author"]
            text = data["text"]
            self.add_message_to_box(author, text)
    
    def clear_chat_history(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.message_row = 0
        self.update_idletasks()
        self._parent_canvas.yview_moveto(1.0)





class MessageSendBox(CTkFrame):
    def __init__(self, master, dialoge_box):
        super().__init__(master)
        self.dialoge_box = dialoge_box
        self.grid_columnconfigure(0, weight=1)

        self.message_textbox = CTkTextbox(self, font=("Arial", 16), fg_color="#2F2F2F", text_color="#ECECEC", height=80, corner_radius=10)
        self.message_textbox.grid(row = 0, column = 0, padx = (10, 10), pady = 10, sticky = "new", columnspan = 2)

        self.message_textbox.bind("<Return>", self.on_enter_pressed)

        self.send_message_button = CTkButton(self, width=40, height=40, text = "Send", command=self.send_message)
        self.send_message_button.grid(row = 1, column = 1, pady = (0, 10), padx = 10, sticky = "es")

        self.delete_chat_history = CTkButton(self, text = "Delete Chat History", command=self.delete_chat_history_command, height = 40)
        self.delete_chat_history.grid(row = 1, column = 0, pady = (0, 10), padx = 10, sticky = "ws")

    def send_message(self):
        self.textbox_text = self.message_textbox.get("0.0", "end").rstrip('\n')
        self.message_textbox.delete("0.0", "end")

        if self.textbox_text.strip() != "":
            DataExchange.update_chat_history(self.textbox_text, "user")
            self.dialoge_box.add_message_to_box("user", self.textbox_text)
             
    def on_enter_pressed(self, event):
        if event.state & 0x0001:  # Shift нажат
            self.message_textbox.insert("insert", "\n")
            return "break"
        else:
            self.send_message()
            return "break"

    def delete_chat_history_command(self):
        DataExchange.clear_chat_history()
        self.dialoge_box.clear_chat_history()
        self.dialoge_box.update_idletasks()
        self.dialoge_box._parent_canvas.yview_moveto(1.0)





class OptionsListBox(CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.settings_button = CTkButton(self, text = "Settings")
        self.settings_button.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = "n")

        self.chat_button = CTkButton(self, text="Chat")
        self.chat_button.grid(row = 1, column = 0, padx = 10, pady = (0, 10), sticky = "n")





gui = GraphicUserInterface()
gui.gui_start()