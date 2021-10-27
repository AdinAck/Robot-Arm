"""
Hardware interface for the FOC Motor Controller
https://github.com/AdinAck/Motor-Controller

Adin Ackerman
"""

from threading import Lock
from itertools import chain
from serial import Serial
from serial.serialutil import SerialException
from typing import Literal, Any


class MotorException(Exception):
    pass


class Motor:
    """
    A Motor object, representing the communication with a single motor

    Attributes
    ----------
    ser: Serial
        Serial object
    port: str
        Serial port
    id: int
        Motor ID for multi-motor systems
    offset: float
        The offset angle of the motor
    lock: Lock
        Thread lock for serial calls
    """
    deviceName: str = 'Adafruit Feather M0'
    m_id: int = -1
    offset: float = 0
    controlMode: Literal['torque', 'velocity', 'angle'] = 'torque'

    def __init__(self, port: str) -> None:
        """
        Parameters
        ----------
        port: str
            Serial port to connect to
        """
        self.port = port
        self.ser = Serial(baudrate=9600, timeout=1)
        self.lock = Lock()

        self.connect()

    def _sendCommand(self, cmd: str, returnType: type) -> Any:
        """
        Send a command to the motor
        *Intended for internal use only*

        Parameters
        ----------
        cmd: str
            Command to send

        Returns
        -------
        str
            Response from motor

        Raises
        ------
        MotorException
        """
        with self.lock:
            try:
                self.ser.write(f'{cmd}\n'.encode())
                r = self.ser.readline().decode().strip()
                # print(self.m_id, cmd, r)
                return returnType(r)
            except ValueError:
                raise MotorException(
                    f'Received data could not be parsed as {returnType}. COM may be out of sync.'
                )

    def connect(self) -> None:
        """
        Establish connection with motor
        """
        self.ser.port = self.port
        self.ser.open()
        try:
            self.m_id = self._sendCommand('I', int)
        except SerialException:
            raise NotImplementedError(
                "Failed to initialize motor: SerialException.")

    def disconnect(self) -> None:
        """
        Disconnect from motor
        """
        self.disable()
        self.ser.close()

    @property
    def alive(self) -> bool:
        """
        Check if motor is alive

        Returns
        -------
        bool
            True if alive, False otherwise
        """
        return self.ser.is_open

    @property
    def COMPrecision(self) -> int:
        """
        Get COM decimal precision

        Returns
        -------
        int
            Current COM precision
        """
        return self._sendCommand('#', int)

    @property
    def enabled(self) -> bool:
        """
        Check if motor is enabled

        Returns
        -------
        bool
            True if enabled, False if disabled
        """
        return self._sendCommand('ME', bool)

    @property
    def position(self) -> float:
        """
        Getter for motor position

        Returns
        -------
        float
            Current position
        """
        return self._sendCommand('MMG6', float) - self.offset

    @property
    def velocity(self) -> float:
        """
        Getter for motor velocity

        Returns
        -------
        float
            Current velocity
        """
        return self._sendCommand('MMG5', float)

    def setCOMPrecision(self, decimals: int) -> None:
        """
        Set number of decimals in COM output

        Parameters
        ----------
        decimals: int
            Number of decimals to use

        Raises
        ------
        MotorException
        """
        assert 1 <= decimals <= 15, 'Decimal precision must be within the range [1,15].'

        if self._sendCommand(f'#{decimals}', float) != decimals:
            raise MotorException(
                "Failed to set COM precision: Mismatched confirmation message.")

    def enable(self) -> None:
        """
        Enable motor

        Raises
        ------
        MotorException
        """
        if self._sendCommand('ME1', int) != 1:
            raise MotorException(
                "Failed to enable motor: Mismatched confirmation message.")

    def disable(self) -> None:
        """
        Disable motor

        Raises
        ------
        MotorException
        """
        if self._sendCommand('ME0', int) != 0:
            raise MotorException(
                "Failed to disable motor: Mismatched confirmation message.")

    def setPIDs(self, stage: Literal['vel', 'angle'], *args: float, **kwargs: float) -> None:
        """
        Set PID values for angle and velocity control

        Parameters
        ----------
        stage: Literal['vel', 'angle']
            Which PID stage to set
        P: float
            Proportional gain
        I: float
            Integral gain
        D: float
            Differential gain
        R: float
            Output ramp
        L: float
            Output limit
        F: float
            Low pass filter time constant

        Raises
        ------
        MotorException
        """
        PIDType = 'A' if stage == 'angle' else 'V'

        for char, arg in chain(zip(['P', 'I', 'D', 'R', 'L', 'F'], args), kwargs.items()):
            if (
                self._sendCommand(
                    f'M{PIDType}{char}{arg}', float
                ) != arg
            ):
                raise MotorException(
                    f"Failed to set PIDs: Mismatched confirmation message.")

    def setCurrentLimit(self, limit: float) -> None:
        """
        Set motor current limit

        Parameters
        ----------
        limit: float
            Limit value

        Raises
        ------
        MotorException
        """
        if self._sendCommand(f'MLC{limit}', float) != limit:
            raise MotorException(
                "Failed to set current limit: Mismatched confirmation message.")

    def setVoltageLimit(self, limit: float) -> None:
        """
        Set motor voltage limit

        Parameters
        ----------
        limit: float
            Limit value

        Raises
        ------
        MotorException
        """
        if self._sendCommand(f'MLU{limit}', float) != limit:
            raise MotorException(
                "Failed to set voltage limit: Mismatched confirmation message.")

    def setVelocityLimit(self, limit: float) -> None:
        """
        Set motor velocity limit

        Parameters
        ----------
        limit: float
            Limit value

        Raises
        ------
        MotorException
        """
        if self._sendCommand(f'MLV{limit}', float) != limit:
            raise MotorException(
                "Failed to set velocity limit: Mismatched confirmation message.")

    def setControlMode(self, mode: Literal['torque', 'velocity', 'angle'] = 'torque') -> None:
        """
        Set control mode

        Parameters
        ----------
        mode: str
            Control mode

            Can be one of 3 literals: 'torque', 'velocity', or 'angle'

        Raises
        ------
        MotorException
        """
        d = {
            'torque': 0,
            'velocity': 1,
            'angle': 2,
        }
        if self._sendCommand(f'MC{d[mode]}', str)[:3] != mode[:3]:
            raise MotorException(
                "Failed to set control mode: Mismatched confirmation message.")
        else:
            self.controlMode = mode

    def move(self, pos: float) -> None:
        """
        Set target position

        Parameters
        ----------
        pos: float
            Target position

        Raises
        ------
        MotorException
        """
        if self.controlMode == 'angle':
            pos = round(pos + self.offset, 3)

        if self._sendCommand(f'M{pos}', float) != pos:
            raise MotorException(
                "Failed to set target position: Mismatched confirmation message.")
