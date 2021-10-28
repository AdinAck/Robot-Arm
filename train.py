import tkinter as tk
import argparse
from widgets._data_collection import TrainApp



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arguments to pass to trainer')
    parser.add_argument('--generations', type=int, default=1, help='Number of epochs to train')
    parser.add_argument('--checkpoint', type=str, default=None, help='File to load model from')
    parser.add_argument('--neat_config', type=str, default='config-feedforward', help='File to load neat config from')
    train_config = parser.parse_args()
    
    root = tk.Tk()
    root.title('SCARA Motion Control System')
    app = TrainApp(train_config, root)
    root.eval('tk::PlaceWindow . center')
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
