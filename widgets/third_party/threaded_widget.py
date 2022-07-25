import tkinter as tk
import tkinter.ttk as ttk

from lib.widget import Widget
from lib.utils import threaded_callback


class ThreadedWidget(Widget):
    # our setup function creates and integrates some UI elements
    def setup(self):
        ttk.Label(self, text='Hello, World!').pack( # create and pack a label
            padx=10, pady=10
        )

        self.button = ttk.Button(  # create a button
            self,
            text='Button',
            command=self._callback # and bind it to a callback
        )                     
        self.button.pack(padx=10, pady=10) # pack button

    # a callback function that is executed in a separate thread
    @threaded_callback
    def _callback(self):
        self.button.config(text='Working...') # change the button text
        self.button.config(state='disabled')  # disable the button

        self.control.move('smooth', x=0, y=20) # move the arm to 0, 20, z=0, r=0, e=0

        self.button.config(state='normal') # enable the button
        self.button.config(text='Button')  # change the button text back
