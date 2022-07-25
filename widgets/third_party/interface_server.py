import tkinter as tk
import tkinter.ttk as ttk
import sys
import socket

from requests import delete

from lib.widget import Widget
from lib.utils import threaded_callback


class Server(Widget):
    # our setup function creates and integrates some UI elements
    def setup(self):
        ttk.Label(self, text="Server Control").pack(  # create and pack a label
            padx=10, pady=10
        )

        self.text = tk.Text(self, height=10, width=50)
        self.text.pack()

        self.button = ttk.Button(  # create a button
            self,
            text="Start Server",
            command=self._callback,  # and bind it to a callback
        )
        self.button.pack(padx=10, pady=10)  # pack button

        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @threaded_callback
    def _callback(self):
        self.button.config(text="Waiting for connection...")
        try:
            self.soc.bind(("localhost", 1023))
        except socket.error as message:
            print(f"Bind failed. Error Code : {str(message[0])} Message {message[1]}")
            sys.exit()
        self.button.config(text="Binded", state="disabled")

        self.soc.listen(10)
        client, _ = self.soc.accept()
        while 1:
            x = client.recv(1024)
            y = client.recv(1024)
            z = client.recv(1024)

            if not x or not y or not z:
                break
            x = x.decode("utf-8")
            y = y.decode("utf-8")
            z = z.decode("utf-8")
            print(f"Received: {x}, {y}, {z}")
            self.text.delete(0, "end")
            self.text.insert(0, f"X: {x}, Y: {y}, Z: {z}")
            self.control.move(x, y, z)

        self.soc.close()
