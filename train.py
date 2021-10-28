import tkinter as tk
import argparse
from widgets._data_collection import TrainApp



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arguments to pass to trainer')
    parser.add_argument('--generations', type=int, default=100, help='Number of epochs to train')
    parser.add_argument('--checkpoint', type=str, default=None, help='File to load model from')
    parser.add_argument('--neat_config', type=str, default='config-feedforward', help='File to load neat config from')
    parser.add_argument('--duration', type=float, default=2, help='Time to run for')
    parser.add_argument('--trials', type=int, default=3, help='Number of trials to run per individual')
    train_config = parser.parse_args()
    
    root = tk.Tk()
    root.title('SCARA Motion Control System')
    app = TrainApp(root, train_config)
    root.eval('tk::PlaceWindow . center')
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
