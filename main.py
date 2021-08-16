from time import sleep
import math
from serial import Serial
from serial.tools.list_ports import comports
from FOCMCInterface import Motor

import tkinter as tk
import tkinter.ttk as ttk

from typing import Optional


class RobotArm:
    """
    A RobotArm object, representing the robot arm and all it's components.

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
    l1: float = 15.5
    l2: float = 15.25
    minimumRadius: float = 10

    def __init__(self):
        devices = [Motor(str(d.device))
                   for d in comports() if d.description == 'Adafruit Feather M0']

        self.motors = {motor.id: motor for motor in devices}

        self.m1 = self.motors[1]
        self.m2 = self.motors[2]
        self.m3 = self.motors[3]
        self.m4 = self.motors[4]

        self.m3.setVoltageLimit(6)
        self.m3.setPIDs('vel', 1, F=0.02)
        self.m3.setPIDs('angle', 20, D=0.1, F=0.02)

        self.m1.setPIDs('vel', 1)
        self.m1.setPIDs('angle', 50, F=0.02)
        self.singleEndedHome(
            self.m1,
            centerOffset=45,
            voltage=3,
            speed=-5,
            zeroSpeed=0.1
        )

        self.absoluteHome(self.m3, 4, 1.25, 7.6)
        self.absoluteHome(self.m4, 6, 3.95, 10.13)
        self.m2.offset = 2.1
        self.m2.setVoltageLimit(12)
        self.m2.setPIDs('vel', 5, 0)
        self.m2.setPIDs('angle', 20)
        self.m2.setControlMode('angle')
        self.m2.enable()
        self.m2.move(0)

    @staticmethod
    def absoluteHome(motor: Motor, threshold: float, centerLow: float, centerHigh: float) -> None:
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

        if (p := motor.position) is not None:
            motor.offset = centerLow if p < threshold else centerHigh

            motor.setControlMode('angle')
            motor.enable()
            motor.move(0)

        else:
            print(f'Motor {motor.id} disconnected.')

    @staticmethod
    def singleEndedHome(motor: Motor, centerOffset: float = 0, voltage: float = 3, speed: float = 1, zeroSpeed: float = 0.1):
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
        print(f'Homing motor {motor.id}')

        angle = 0

        motor.setVoltageLimit(voltage)
        motor.setControlMode('velocity')
        motor.move(speed)
        motor.enable()

        sleep(1)

        while (v := motor.velocity) is not None and abs(v) > zeroSpeed:
            # print(v)
            sleep(.1)

        motor.move(0)

        if (p := motor.position) is not None:
            angle = p

        motor.offset = angle
        motor.setControlMode('angle')
        motor.move(centerOffset)

    def cartesianToDualPolar(self, x: float, y: float):
        r = (x**2 + y**2)**0.5
        a = math.atan2(y, x)

        if y >= 0:
            t1 = a - math.acos(
                (
                    r**2 + self.l1**2 - self.l2 ** 2
                ) / (
                    2 * r * self.l1
                )
            )
            t2 = math.pi - math.acos(
                (
                    self.l1**2 + self.l2**2 - r**2
                ) / (
                    2 * self.l1 * self.l2
                )
            )
        else:
            t1 = a + math.acos(
                (
                    r**2 + self.l1**2 - self.l2 ** 2
                ) / (
                    2 * r * self.l1
                )
            )
            t2 = -math.pi + math.acos(
                (
                    self.l1**2 + self.l2**2 - r**2
                ) / (
                    2 * self.l1 * self.l2
                )
            )

        if (x**2 + y**2)**0.5 > self.minimumRadius:
            return t1, t2
        else:
            return self.cartesianToDualPolar(
                (self.minimumRadius+0.1)*math.cos(a), (self.minimumRadius+0.1)*math.sin(a))


class Popup(tk.Toplevel):
    def __init__(self, parent, title=None):
        tk.Toplevel.__init__(self, parent)
        self.title(title)
        self.grab_set()

    def destroy(self):
        self.grab_release()
        tk.Toplevel.destroy(self)


class Application(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.pack(fill='both', expand=True)

        # Variables
        self.robotarm = RobotArm()
        self.targetXVar = tk.DoubleVar()
        self.targetYVar = tk.DoubleVar()
        self.targetZVar = tk.DoubleVar()

        # Widgets
        self.contentFrame = ttk.Frame(self)
        self.contentFrame.grid(row=1, column=0, sticky='WE')

        self.motorConfigButton = ttk.Button(
            self.contentFrame,
            text='Configure Motors',
            command=self.configureMotorsPanel
        )
        self.motorConfigButton.grid(row=0, column=0, sticky='E')

        self.targetXLabel = ttk.Label(self.contentFrame, text='Target X:')
        self.targetXLabel.grid(row=1, column=0, sticky='E')

        self.targetXEntry = ttk.Entry(
            self.contentFrame,
            textvariable=self.targetXVar,
            width=10
        )
        self.targetXEntry.grid(row=1, column=1, sticky='W')
        self.targetXEntry.bind('<Return>', lambda _: self.jog())

        self.targetXSlider = ttk.Scale(
            self.contentFrame,
            variable=self.targetXVar,
            command=lambda x: self.updateTargets(x=round(float(x), 1)),
            from_=0,
            to=30,
            orient='horizontal'
        )
        self.targetXSlider.grid(row=1, column=2, sticky='W')

        self.targetYLabel = ttk.Label(self.contentFrame, text='Target Y:')
        self.targetYLabel.grid(row=2, column=0, sticky='E')

        self.targetYEntry = ttk.Entry(
            self.contentFrame,
            textvariable=self.targetYVar,
            width=10
        )
        self.targetYEntry.grid(row=2, column=1, sticky='W')
        self.targetYEntry.bind('<Return>', lambda _: self.jog())

        self.targetYSlider = ttk.Scale(
            self.contentFrame,
            variable=self.targetYVar,
            command=lambda y: self.updateTargets(y=round(float(y), 1)),
            from_=-30,
            to=30,
            orient='horizontal'
        )
        self.targetYSlider.grid(row=2, column=2, sticky='W')

        self.targetZLabel = ttk.Label(self.contentFrame, text='Target Z:')
        self.targetZLabel.grid(row=3, column=0, sticky='E')

        self.targetZEntry = ttk.Entry(
            self.contentFrame,
            textvariable=self.targetZVar,
            width=10
        )
        self.targetZEntry.grid(row=3, column=1, sticky='W')
        self.targetZEntry.bind('<Return>', lambda _: self.jog())

        self.targetZSlider = ttk.Scale(
            self.contentFrame,
            variable=self.targetZVar,
            command=lambda z: self.updateTargets(z=round(float(z), 1)),
            from_=0,
            to=90,
            orient='horizontal'
        )
        self.targetZSlider.grid(row=3, column=2, sticky='W')

        self.requiresConnectedMotors = []
        self.assignedPerMotor = []

    def configureMotorsPanel(self):
        popup = Popup(self, 'Configure Motors')

        topFrame = ttk.Frame(popup)
        topFrame.pack(side='top')

        bottomFrame = ttk.Frame(popup)
        bottomFrame.pack(side='bottom', fill='x')

        contentFrame = ttk.Frame(popup)
        contentFrame.pack(side='bottom', fill='x', expand=True)

        s = tk.StringVar()
        motorSelect = ttk.OptionMenu(
            topFrame, s, f'Motor {list(self.robotarm.motors.keys())[0]}', *[f'Motor {id}' for id in self.robotarm.motors])
        # motorSelect = ttk.OptionMenu(
        #     topFrame, s, 'Motor 1', 'Motor 1', 'Motor 2', 'Motor 3', 'Motor 4')
        motorSelect.pack(side='top')

        ttk.Button(
            bottomFrame,
            text='Apply',
            command=popup.destroy
        ).pack(side='right')

        ttk.Button(
            bottomFrame,
            text='Cancel',
            command=popup.destroy
        ).pack(side='right')

        ttk.Button(
            bottomFrame,
            text='Ok',
            command=popup.destroy
        ).pack(side='right')

        self.voltageLimitVar = tk.DoubleVar()

        self.voltageLimitLabel = ttk.Label(contentFrame, text='Voltage Limit:')
        self.voltageLimitLabel.grid(row=0, column=0, sticky='E')

        self.voltageLimitEntry = ttk.Entry(
            contentFrame,
            textvariable=self.voltageLimitVar,
            width=4
        )
        self.voltageLimitEntry.grid(row=0, column=1, sticky='W')

    def updateTargets(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None):
        if x is not None:
            self.targetXVar.set(x)
        if y is not None:
            self.targetYVar.set(y)
        if z is not None:
            self.targetZVar.set(z)

        self.jog()

    def jog(self):
        t1, t2 = self.robotarm.cartesianToDualPolar(
            self.targetXVar.get(), self.targetYVar.get()
        )

        self.robotarm.m2.move(t1)
        self.robotarm.m3.move(t2)
        self.robotarm.m1.move(self.targetZVar.get())


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Robot Arm')
    app = Application(root)
    app.mainloop()
