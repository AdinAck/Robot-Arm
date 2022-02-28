import math
from serial.tools.list_ports import comports
from time import time, sleep
from typing import Optional, Callable

from tkinter import messagebox

from hardware.FOCMCInterface import Motor, MotorException
from hardware.EndEffector import EndEffectorException
from hardware.FOCBLDCEndEffector import FOCBLDC as EndEffector

from lib.bezier import bezier


class System:
    """
    A System object, representing the robot arm and all it's components.

    Attributes
    ----------
    motors: dict[int, Motor]
        A dictionary of all the motor objects in the system.
    m_vertical: Motor
        Motor 1, the vertical translation motor.
    m_inner_rot: Motor
        Motor 2, the first rotation motor (theta1).
    m_outer_rot: Motor
        Motor 3, the second rotation motor (theta2).
    m_end_rot: Motor
        Motor 4, the end effector motor.
    """

    # Only one instance of System is intended to exist at a time.
    motors: dict[int, Motor] = {}
    l1: float = 15.5
    l2: float = 15.25
    minimum_radius: float = 15

    def __init__(self):
        """
        Initialize System object.

        Connect to all devices and configure motors.
        """
        ports_used = []

        for d in comports():
            try:
                m = Motor(str(d.device))
                if 0 < m.m_id < 5:
                    self.motors[m.m_id] = m
                    ports_used.append(str(d.device))
                else:
                    m.disconnect()
            except MotorException:
                continue
    

        for d in comports():
            if str(d.device) not in ports_used:
                try:
                    self.end_effector = EndEffector(str(d.device))
                    break
                except EndEffectorException:
                    continue
        
        try:
            self.m_vertical = self.motors[1]
            self.m_inner_rot = self.motors[2]
            self.m_outer_rot = self.motors[3]
            self.m_end_rot = self.motors[4]
        except KeyError:
            msg = 'A serial connection could not be established with at least one motor. ' \
                + f'Detected motor(s): {[id for id in self.motors]}'
            messagebox.showerror(__name__, msg)
            raise

        try:
            self.end_effector
        except AttributeError:
            msg = 'A serial connection could not be established with the end effector.'
            messagebox.showerror(__name__, msg)
            raise


        # All below should be somehow defined in a file or something
        # maybe defer to loadMotors?
        self.joints = {
            't1': self.m_inner_rot,
            't2': self.m_outer_rot,
            'z': self.m_vertical,
            'r': self.m_end_rot,
        }


        self.m_vertical.set_voltage_limit(12)
        self.m_vertical.set_PIDs('vel', 0.5, 20)
        self.m_vertical.set_PIDs('angle', 10)

        self.m_inner_rot.set_voltage_limit(12)
        self.m_inner_rot.set_velocity_limit(4)
        self.m_inner_rot.set_PIDs('vel', 2, 20, R=200, F=0.01)
        self.m_inner_rot.set_PIDs('angle', 20, D=4, R=125, F=0.01)

        self.m_outer_rot.set_voltage_limit(12)
        self.m_outer_rot.set_velocity_limit(4)
        self.m_outer_rot.set_PIDs('vel', 0.6, 20, F=0.01)
        self.m_outer_rot.set_PIDs('angle', 20, D=3, R=100, F=0.01)

        self.m_end_rot.set_voltage_limit(12)
        self.m_end_rot.set_velocity_limit(12)


    def load_motors(self, onFail: Optional[Callable] = None):
        """
        Load motor calibration from disk.

        *This function will cause movement.

        Parameters
        ----------
        onFail: Optional[Callable]
            Callback for if files are not found or corrupted.
        """


        self.single_ended_home(self.m_vertical, 140/2, -4)
        self.end_effector.enable()
        self.auto_calibrate(
            self.end_effector.m, voltage=2, speed=15, zeroSpeed=10
        )
        self.end_effector.m.set_voltage_limit(6)
        self.end_effector.m.set_velocity_limit(999)

        try:
            with open('config/inner_rot', 'r') as f:
                self.absolute_home(
                    self.m_inner_rot, *(float(f.readline().strip())
                                        for _ in range(3))
                )

            with open('config/outer_rot', 'r') as f:
                self.absolute_home(
                    self.m_outer_rot, *(float(f.readline().strip())
                                        for _ in range(3))
                )

            with open('config/end_rot', 'r') as f:
                self.absolute_home(
                    self.m_end_rot, *(float(f.readline().strip())
                                      for _ in range(3))
                )
        except (FileNotFoundError, ValueError):
            if onFail is not None:
                onFail()
            else:
                msg = 'Failed to load motor config from disk.'
                raise NotImplementedError()
        

    def motors_enabled(self, value: bool):
        """
        Helper function to enable or disable all motors.

        Parameters
        ----------
        value: bool
            Whether to enable or disable all motors.
        """
        f = Motor.enable if value else Motor.disable
        for motor in self.motors.values():
            f(motor)

    @staticmethod
    def auto_calibrate(
        motor: Motor, voltage: float = 3, speed: float = 1, zeroSpeed: float = 0.1
    ) -> tuple[float, float, float]:
        """
        For motors with limited range of motion, move the motor back and forth
        to detect the bounds and interpolate the center position.

        Parameters
        ----------
        motor: Motor
            The motor to calibrate.
        voltage: float
            The voltage to use for calibration.
        speed: float
            The speed to use for calibration.
        zeroSpeed: float
            The threshold speed to be considered zero.

        Returns
        -------
        tuple[float, float, float]
            The minimum, maximum, and center position of the motor.
        """
        try:
            low, high = 0, 0

            motor.set_voltage_limit(voltage)
            motor.set_control_mode('velocity')
            motor.move(-speed)
            motor.enable()

            sleep(1)

            while abs(motor.velocity) > zeroSpeed:
                sleep(0.1)

            motor.move(0)

            low = motor.position

            motor.move(speed)

            sleep(1)

            while abs(motor.velocity) > zeroSpeed:
                sleep(0.1)

            motor.move(0)

            high = motor.position

            motor.offset = (low + high) / 2
            motor.set_control_mode('angle')
            motor.move(0)

            return low, high, motor.offset
        except MotorException:
            raise NotImplementedError('Failed to calibrate motor.')

    @staticmethod
    def absolute_home(motor: Motor, low: float, high: float, center: float) -> None:
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
                motor.offset = center - 2 * math.pi
            else:
                motor.offset = center + 2 * math.pi

            motor.set_control_mode('angle')
            motor.move(0)
            motor.enable()

        except MotorException:
            raise NotImplementedError('Failed to home motor.')

    @staticmethod
    def single_ended_home(
        motor: Motor,
        centerOffset: float = 0,
        voltage: float = 3,
        zeroSpeed: float = 0.1,
        active: bool = True,
    ) -> float:
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

            motor.set_control_mode('torque')
            motor.move(voltage)
            motor.enable()

            sleep(1)

            while abs(motor.velocity) > zeroSpeed:
                sleep(0.1)

            motor.move(0)

            angle = motor.position

            if active:
                motor.offset = angle
                motor.set_control_mode('angle')
                motor.move(centerOffset)
            else:
                motor.disable()

            return angle
        except MotorException:
            raise NotImplementedError('Failed to home motor.')

    def polar_to_cartesian(self, t1: float, t2: float) -> tuple[float, float]:
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
        return self.l1 * math.cos(-t1) + self.l2 * math.cos(
            -t2 - t1
        ), self.l1 * math.sin(t1) + self.l2 * math.sin(t2 + t1)

    def cartesian_to_dual_polar(self, x: float, y: float):
        """
        Convert cartesian coordinates to cascaded polar coordinates.

        (x, y) -> (t1, t2)

        Parameters
        ----------
        x: float
            The x-coordinate of the end effector.
        y: float
            The y-coordinate of the end effector.

        Returns
        -------
        tuple[float, float]
            The angle of the first motor and the angle of the second motor.
        """
        r = abs(complex(x, y))
        a = math.atan2(y, x)

        if r <= self.minimum_radius:
            return self.cartesian_to_dual_polar(
                (self.minimum_radius + 0.1) * math.cos(a),
                (self.minimum_radius + 0.1) * math.sin(a),
            )
        elif r > self.l1 + self.l2:
            return a, 0

        # This section is adapted by Daniel from the original inverse kinematics math by Adin.
        # start
        acos_value = math.acos(
            (r ** 2 + self.l1 ** 2 - self.l2 ** 2) / (2 * self.l1 * r)
        )
        t2 = math.pi - math.acos(
            (self.l1 ** 2 + self.l2 ** 2 - r ** 2) / (2 * self.l1 * self.l2)
        )
        if y >= 0:
            acos_value = -acos_value
        else:
            t2 = -t2

        t1 = a + acos_value
        # end

        return t1, t2

    def get_all_pos(self):
        """
        Retrieve all motor positions.

        Returns
        -------
        Generator[float]
            A generator of all motor positions.
        """
        return (m.position for m in self.joints.values())

    def jog(self, t1: float, t2: float, r: float, z: float, e: Optional[int] = None):
        """
        Instruct the motors to move to the given position.
        This directly calls the Motor.move method, so no
        inverse kinematics are performed.

        The orientation of the end effector is relative
        to the world, not to the joint.

        Parameters
        ----------
        t1: float
            The angle of the first motor.
        t2: float
            The angle of the second motor.
        r: float
            The angle of the end effector.
        z: float (WIP)
            The position of the vertical motor.
            (rad right now, should be cm)
        e: Optional[int]
            Arbitrary value given to the installed end effector.
        """
        self.joints['t1'].move(t1)
        self.joints['r'].move(r - t1)

        self.joints['t2'].move(t2)
        self.joints['z'].move(z)

        if e is not None:
            self.end_effector.move(e)

    def smooth_move(self, duration: float, timeout: float = 1, epsilon: float = 0.1, **target) -> None:
        """
        Smoothly move the motors to a target position.

        This function is intended to be launched in a thread.

        Parameters
        ----------
        duration: Optional[float]
            The duration of the movement.
        timeout: Optional[float]
            The amount of time allotted to the move before a timeout exception is raised.
        epsilon: Optional[float]
            The amount of error allowed before the move is considered complete.
        **target: float
            The target position of the motors.
        """
        try:
            t1, t2, z, r = self.get_all_pos()

            start = {'t1': t1, 't2': t2, 'z': z, 'r': r + t1}

            self.jog(**start, e=target['e'])
            start_time = time()
            while (t := time() - start_time) < duration:
                self.jog(
                    **{
                        axis: bezier(
                            0,
                            start[axis],
                            duration / 2,
                            start[axis],
                            duration / 2,
                            target[axis],
                            duration,
                            target[axis],
                            t,
                        )
                        for axis in start
                    }
                )

            start_time = time()
            while time() - start_time < timeout:
                sleep(0.1)
                p1, p2, p3, p4 = self.get_all_pos()

                if (
                    abs(target['t1'] - p1) < epsilon
                    and abs(target['t2'] - p2) < epsilon
                    and abs(target['z'] - p3) < epsilon
                    and abs(target['r'] - p4 - p1) < epsilon
                ):
                    break
            else:
                msg = 'Motors did not reach target position in the allotted time.'
                messagebox.showwarning(__name__, msg)
                raise NotImplementedError(msg)

        except MotorException:
            msg = 'Failed to smooth move.'
            messagebox.showwarning(__name__, msg)
            raise NotImplementedError(msg)
