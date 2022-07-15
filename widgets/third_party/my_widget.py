import tkinter as tk
import tkinter.ttk as ttk

from lib.widget import Widget

class MyWidget(Widget):
    def setup(self):
        ttk.Label(self, text='Hello, World!').pack(padx=10, pady=10)
    
        ttk.Button(self, text='Button', command=self._callback).pack(padx=10, pady=10)

    def _callback(self):
        self.control.move('smooth', x=0, y=20)