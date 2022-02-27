from .FOCMCInterface import Motor, MotorException
from .EndEffector import EndEffector, EndEffectorException


class FOCBLDC(EndEffector):
    """
    A Servo object represneting the interface with a servo motor, inheriting from EndEffector.
    """
    deviceName: str = 'Adafruit Feather M0'

    def __init__(self, port: str):
        try:
            self.m = Motor(port)
            if self.m.m_id != 5:
                raise EndEffectorException('Motor does not conform to ID protocol.')
        except MotorException:
            raise EndEffectorException('Could not assertain motor ID.')
        self.m.set_control_mode('angle')
        self.m.set_voltage_limit(6)

    @property
    def value_range(self) -> tuple[int, int]:
        return 0, 100

    def connect(self) -> None:
        try:
            self.m.connect()
        except:
            raise EndEffectorException('Could not connect to end effector.')

    def disconect(self) -> None:
        try:
            self.m.disconnect()
        except:
            raise EndEffectorException(
                'Could not disconnect from end effector.')

    def enable(self) -> None:
        self.m.enable()

    def disable(self) -> None:
        self.m.disable()

    def move(self, target: int) -> None:
        try:
            # target ranges from 0-100
            # motor can move from -2.5-2.5
            self.m.move(9*(target-50)/20)
        except MotorException:
            raise EndEffectorException('Could not move end effector.')
