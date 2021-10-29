import tkinter as tk
import argparse
from widgets._data_collection import TrainApp



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arguments to pass to trainer')
    train_config = parser.parse_args()
    
    root = tk.Tk()
    root.title('SCARA Motion Control System')
    app = TrainApp(root, train_config)
    root.eval('tk::PlaceWindow . center')
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
