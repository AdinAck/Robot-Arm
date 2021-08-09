from serial import Serial
from serial.tools.list_ports import comports
from FOCMCInterface import Motor

devices = [Motor(str(d.device))
           for d in comports() if d.description == 'Adafruit Feather M0']

motors = {motor.id: motor for motor in devices}

m1 = motors[1]
m2 = motors[2]
m3 = motors[3]
m4 = motors[4]

m2.setPIDs('vel', 5)
m2.setPIDs('angle', 20, D=5)
m3.setPIDs('vel', 1)
m3.setPIDs('angle', 20, D=5, F=0.02)

for m in devices:
    m.setControlMode('angle')
    m._sendCommand('MLU12', float)
