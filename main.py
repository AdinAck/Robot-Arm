import tkinter as tk
from lib.app import Application

if __name__ == "__main__":
    root = tk.Tk()
    root.title("SCARA Motion Control System")
    app = Application(root)
    root.eval("tk::PlaceWindow . center")
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
