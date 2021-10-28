import math
from serial.tools.list_ports import comports
import tkinter as tk
from time import time, sleep
from typing import Optional, Callable

from warnings import warn

from hardware.FOCMCInterface import Motor, MotorException
from hardware.ServoInterface import Servo as EndEffector

from lib.bezier import bezier


class System:
    """
    A System object, representing the robot arm and all it's components.

    Attributes
    ----------
    motors: dict[int, Motor]
        A dictionary of all the motor objects in the system.
    m1: Motor
        Motor 1, the vertical translation motor.
    m2: Motor
        Motor 2, the first rotation motor (theta1).
    m3: Motor
        Motor 3, the second rotation motor (theta2).
    m4: Motor
        Motor 4, the end effector motor.
    """

    # Only one instance of System is intended to exist at a time.
    motors: dict[int, Motor] = {}
    l1: float = 15.5
    l2: float = 15.25
    minimumRadius: float = 10

    def __init__(self):
        try:
            for d in comports():
                try:
                    m = Motor(str(d.device))
                    self.motors[m.m_id] = m
                except:
                    # raise NotImplementedError('Unidentifiable motor.')
                    try:
                        self.endEffector = EndEffector(str(d.device))
                    except:
                        pass

            self.m1 = self.motors[1]
            self.m2 = self.motors[2]
            self.m3 = self.motors[3]
            self.m4 = self.motors[4]

            # All below should be somehow defined in a file or something
            self.joints = {
                't1': self.m2,
                't2': self.m3,
                'z':  self.m1,
                'r':  self.m4,
            }

            self.m1.setVoltageLimit(12)
            self.m1.setPIDs('vel', .5, 20)
            self.m1.setPIDs('angle', 10)

            self.m2.setVoltageLimit(12)
            self.m2.setVelocityLimit(2)
            self.m2.setPIDs('vel', 2, 20, R=200, F=0.01)
            self.m2.setPIDs('angle', 30, D=4, R=125, F=0.01)

            self.m3.setVoltageLimit(12)
            self.m3.setVelocityLimit(4)
            self.m3.setPIDs('vel', .6, 20, F=0.01)
            self.m3.setPIDs('angle', 20, D=3, R=100, F=0.01)

            self.m4.setVelocityLimit(1)

        except KeyError:
            raise NotImplementedError(
                'A serial connection could not be established with at least one motor.')

    def loadMotors(self, onFail: Optional[Callable] = None):
        self.singleEndedHome(self.m1, 45, -2)

        try:
            with open('config/m2', 'r') as f:
                self.absoluteHome(self.m2, *(float(f.readline().strip())
                                             for _ in range(3)))

            with open('config/m3', 'r') as f:
                self.absoluteHome(self.m3, *(float(f.readline().strip())
                                             for _ in range(3)))

            with open('config/m4', 'r') as f:
                self.absoluteHome(self.m4, *(float(f.readline().strip())
                                             for _ in range(3)))
        except (FileNotFoundError, ValueError):
            if onFail is not None:
                onFail()
            else:
                raise NotImplementedError(
                    "Failed to load motor config from disk.")

    def motorsEnabled(self, value: bool):
        f = Motor.enable if value else Motor.disable
        for motor in self.motors.values():
            f(motor)

    @staticmethod
    def autoCalibrate(motor: Motor, voltage: float = 3, speed: float = 1, zeroSpeed: float = 0.1) -> tuple[float, float, float]:
        try:
            low, high = 0, 0

            motor.setVoltageLimit(voltage)
            motor.setControlMode('velocity')
            motor.move(-speed)
            motor.enable()

            sleep(1)

            while abs(motor.velocity) > zeroSpeed:
                sleep(.1)

            motor.move(0)

            low = motor.position

            motor.move(speed)

            sleep(1)

            while abs(motor.velocity) > zeroSpeed:
                sleep(.1)

            motor.move(0)

            high = motor.position

            motor.offset = (low+high)/2
            motor.setControlMode('angle')
            motor.move(0)

            return low, high, motor.offset
        except MotorException:
            raise NotImplementedError('Failed to calibrate motor.')

    @staticmethod
    def absoluteHome(motor: Motor, low: float, high: float, center: float) -> None:
        """
        Determine the zero position of a motor with movement limited to less than 1 full rotation.

        Parameters
        ----------
        motor: Motor
            The motor whose zero position is to be determined.
        centerOffset: float
            The offset from the center of the motor to the zero position.

        Raises
        ------
        AssertionError
            If the given centerOffset is invalid.
        """

        try:
            p = motor.position
            if low <= p <= high:
                motor.offset = center
            elif p < low:
                motor.offset = center - 2*math.pi
            else:
                motor.offset = center + 2*math.pi

            motor.setControlMode('angle')
            motor.move(0)
            motor.enable()

        except MotorException:
            raise NotImplementedError('Failed to home motor.')

    @staticmethod
    def singleEndedHome(motor: Motor, centerOffset: float = 0, voltage: float = 3, zeroSpeed: float = 0.1, active: bool = True) -> float:
        """
        Determine the position of a motor with multi-rotation movement using one extreme.

        Parameters
        ----------
        motor: Motor
            The motor whose position is to be determined.
        centerOffset: float
            The offset from the center of the motor to the zero position.
        voltage: float
            The voltage to be set on the motor.
        speed: float
            The speed to be used during homing.
        zeroSpeed: float
            The threshold speed to determine no movement.
        """

        try:
            angle = 0

            motor.setControlMode('torque')
            motor.move(voltage)
            motor.enable()

            sleep(1)

            while abs(motor.velocity) > zeroSpeed:
                sleep(.1)

            motor.move(0)

            angle = motor.position

            if active:
                motor.offset = angle
                motor.setControlMode('angle')
                motor.move(centerOffset)
            else:
                motor.disable()

            return angle
        except MotorException:
            raise NotImplementedError('Failed to home motor.')

    def polarToCartesian(self, t1: float, t2: float) -> tuple[float, float]:
        """
        Convert polar coordinates to cartesian.

        Parameters
        ----------
        t1: float
            The angle of the first motor.
        t2: float
            The angle of the second motor.

        Returns
        -------
        tuple[float, float]
            The cartesian coordinates of the end effector.
        """
        return self.l1*math.cos(-t1) + self.l2*math.cos(-t2-t1), self.l1*math.sin(t1) + self.l2*math.sin(t2+t1)

    def cartesianToDualPolar(self, x: float, y: float):
        r = abs(complex(x, y))
        a = math.atan2(y, x)

        if r <= self.minimumRadius:
            return self.cartesianToDualPolar(
                (self.minimumRadius+0.1)*math.cos(a), (self.minimumRadius+0.1)*math.sin(a))
        elif r > self.l1 + self.l2:
            return a, 0

        # This section is adapted by Daniel from the original inverse kinematics math by Adin.
        # start
        acos_value = math.acos(
            (r**2 + self.l1**2 - self.l2**2) / (2*self.l1*r))
        t2 = math.pi - math.acos((self.l1**2 + self.l2**2 - r**2) /
                                 (2 * self.l1 * self.l2))
        if y >= 0:
            acos_value = -acos_value
        else:
            t2 = -t2

        t1 = a + acos_value
        # end

        return t1, t2

    def getAllPos(self):
        return (m.position for m in self.joints.values())

    def jog(self, t1, t2, r, z, e=None):
        self.joints['t1'].move(t1)
        self.joints['r'].move(r-t1)

        self.joints['t2'].move(t2)
        self.joints['z'].move(z)

        if e is not None:
            self.endEffector.move(e)

    def smoothMove(self, duration, timeout=1, epsilon=0.1, **end) -> None:
        """
        Smoothly move the motors to a target position.

        This function is intended to be launched in a thread.
        """

        try:
            t1, t2, z, r = self.getAllPos()

            start = {'t1': t1, 't2': t2, 'z': z, 'r': r+t1}

            self.jog(**start, e=end['e'])
            startTime = time()
            while (t := time() - startTime) < duration:
                self.jog(**{axis: bezier(0, start[axis], duration/2, start[axis],
                                         duration/2, end[axis], duration, end[axis], t) for axis in start})

            startTime = time()
            while time() - startTime < timeout:
                sleep(0.1)
                p1, p2, p3, p4 = self.getAllPos()

                if abs(end['t1']-p1) < epsilon and abs(end['t2']-p2) < epsilon and abs(end['z']-p3) < epsilon and abs(end['r']-p4-p1) < epsilon:
                    break
            else:
                raise NotImplementedError(
                    'Motors did not reach target position in the alloted time.')

        except MotorException:
            raise NotImplementedError('Failed to smooth move.')
