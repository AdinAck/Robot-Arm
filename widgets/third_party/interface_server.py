import tkinter as tk
import tkinter.ttk as ttk
import sys
import struct
import socket

from requests import delete

from lib.widget import Widget
from lib.utils import threaded_callback


class Server(Widget):
    running: bool
    # our setup function creates and integrates some UI elements
    def setup(self):
        ttk.Label(self, text="Server Control").pack(  # create and pack a label
            padx=10, pady=10
        )

        self.button = ttk.Button(  # create a button
            self,
            text="Start Server",
            command=self._callback,  # and bind it to a callback
        )
        self.button.pack(padx=10, pady=10)  # pack button
        self.running = True
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @threaded_callback
    def _callback(self):
        self.button.config(text="Binding...", state="disabled")
        try:
            self.soc.bind(("localhost", 1023))
        except socket.error as message:
            # print(f"Bind failed. Error Code : {str(message[0])} Message {message[1]}")
            sys.exit()

        self.button.config(text="Waiting for client...", state="disabled")
        self.soc.listen(10)
        client, _ = self.soc.accept()
        self.button.config(text="Connected")
        while self.running:
            b = client.recv(1)
            if struct.unpack("c", b)[0] == b"\x01":
                x = client.recv(4)
                y = client.recv(4)
                z = client.recv(4)
                x = struct.unpack("f", x)[0]
                y = struct.unpack("f", y)[0]
                z = struct.unpack("f", z)[0]
                print(f"Received: {x}, {y}, {z}")
                self.control.move(x=x, y=y, z=z)

            e = client.recv(4)
            e = struct.unpack("<I", e)[0]
            self.control.move(e=e)

            m1_rot = self.control._system.m_inner_rot.position
            m2_rot = self.control._system.m_outer_rot.position
            z_pos = self.control._system.m_vertical.position
            r_pos = self.control._system.m_end_rot.position

            client.send(struct.pack("f", m1_rot))
            client.send(struct.pack("f", m2_rot))
            client.send(struct.pack("f", z_pos))
            client.send(struct.pack("f", r_pos-m2_rot))
        else:
            self.soc.close()
            client.close()

    def close(self):
        self.running = False
        super().close()
