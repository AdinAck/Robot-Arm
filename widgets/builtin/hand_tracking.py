from http import client
import socket
from threading import Thread

from lib.widget import Widget


class HandTracking(Widget):
    def setup(self):
        self.running = True
        self.clients = {}
        self.max_connections = 1

        self._create_socket()
        Thread(target=self.main, daemon=True).start()

    # create socket server
    def _create_socket(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind(('', 1234))
        self.s.listen()
        self.conn, self.addr = self.s.accept()
        self.conn.settimeout(1)
        print('Connection address:', self.addr)

    def main(self):
        while True:
            clientsocket, address = self.s.accept()
            print(f'Connection from {address} has been established.')
            try:
                while True:
                    # receive comma separated string from client
                    buffer = ""
                    while buffer[-1] != '\n':
                        buffer += clientsocket.recv(1).decode()

                    names = ['x', 'y', 'z']
                    data = {name: float(s) for name, s in zip(
                        names, buffer.split(','))}
                    self.control.move(**data, e=None)
            except:
                continue
