from customtkinter import *
class GraphicUserInterface(CTk):
    def __init__(self):
        self.gui_main = CTk()
        self.gui_main.geometry("900x675")
        self.gui_main.title("AI-Ассистент")
        self.gui_main.mainloop()
        
        
gui = GraphicUserInterface()