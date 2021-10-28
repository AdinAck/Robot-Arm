from serial import Serial
from serial.serialutil import SerialException
from .EndEffector import EndEffector, EndEffectorException


class Servo(EndEffector):
    """
    A Servo object represneting the interface with a servo motor, inheriting from EndEffector.
    """
    deviceName: str = 'Adafruit Trinket M0'

    def __init__(self, port: str):
        self.port = port
        self.ser = Serial(baudrate=9600, timeout=1)
        self.connect()

    @property
    def valueRange(self) -> tuple[int, int]:
        return 10, 150

    def connect(self) -> None:
        try:
            self.ser.port = self.port
            self.ser.open()
        except SerialException as e:
            print(e)
            raise EndEffectorException('Could not connect to end effector.')

    def disconect(self) -> None:
        try:
            self.disable()
            self.ser.close()
        except SerialException:
            raise EndEffectorException(
                'Could not disconnect from end effector.')

    def enable(self) -> None:
        pass

    def disable(self) -> None:
        pass

    def move(self, target: int) -> None:
        try:
            self.ser.write(
                f'{min(self.valueRange[1], max(target, self.valueRange[0]))}\n'.encode())
        except SerialException:
            raise EndEffectorException('Could not move end effector.')
