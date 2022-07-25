import tkinter as tk
import tkinter.ttk as ttk

from lib.widget import Widget


class MyWidget(Widget):
    # our setup function creates and integrates some UI elements
    def setup(self):
        # the parent of our elements is 'self' because our class is a tk window
        ttk.Label(self, text='Hello, World!').pack( # create and pack a label
            padx=10, pady=10
        )

        self.button = ttk.Button(  # create a button
            self,
            text='Button',
            command=self._callback # and bind it to a callback
        )
        self.button.pack(padx=10, pady=10) # pack button

    # just a regular old function that we want the button to execute
    def _callback(self):
        self.control.move('smooth', x=0, y=20) # move the arm to 0, 20, z=0, r=0, e=0
