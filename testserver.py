import socket
import struct

soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.bind(("localhost", 1023))

soc.listen(10)
client, _ = soc.accept()
while 1:
    b = client.recv(1)
    if struct.unpack("c", b)[0] == b"\x01":
        x = client.recv(4)
        y = client.recv(4)
        z = client.recv(4)
        x = struct.unpack("f", x)[0]
        y = struct.unpack("f", y)[0]
        z = struct.unpack("f", z)[0]
        print(f"Received: {x}, {y}, {z}")

    e = client.recv(4)
    e = struct.unpack("<I", e)[0]
    print(f"Received: {e}")

    client.send(struct.pack("f", 1))
    client.send(struct.pack("f", 1))
    client.send(struct.pack("f", 1))
    client.send(struct.pack("f", 1))
