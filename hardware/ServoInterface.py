from serial import Serial
from .EndEffector import EndEffector


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
        self.ser.port = self.port
        self.ser.open()

    def disconect(self) -> None:
        self.disable()
        self.ser.close()

    def enable(self) -> bool:
        # No use for this method
        return True

    def disable(self) -> bool:
        # No use for this method
        return True

    def move(self, target: int) -> bool:
        self.ser.write(
            f'{min(self.valueRange[1], max(target, self.valueRange[0]))}\n'.encode())
        return True  # No means of verifying if the move was successful
