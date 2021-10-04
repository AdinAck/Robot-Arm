from threading import Thread
from serial.tools.list_ports import comports
from time import time, sleep
import math

from lib.bezier import bezier
from lib.gcode import readGcodeLine, writeGcodeLine

from hardware.FOCMCInterface import Motor
from hardware.ServoInterface import Servo as EndEffector

import tkinter as tk
from tkinter import filedialog as fd
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

    # Only one instance of RobotArm is intended to exist at a time.
    motors: dict[int, Motor] = {}
    l1: float = 15.5
    l2: float = 15.25
    minimumRadius: float = 10

    def __init__(self, app):
        self.app = app
        try:

            for d in comports():
                if d.description == Motor.deviceName:
                    m = Motor(str(d.device))
                    if (m_id := m.m_id) is not None:
                        self.motors[m_id] = m
                    else:
                        raise NotImplementedError('Unidentifiable motor.')
                elif d.description == EndEffector.deviceName:
                    self.endEffector = EndEffector(str(d.device))

            self.m1 = self.motors[1]
            self.m2 = self.motors[2]
            self.m3 = self.motors[3]
            self.m4 = self.motors[4]

            self.m1.setVoltageLimit(12)
            self.m1.setPIDs('vel', .5, 20)
            self.m1.setPIDs('angle', 10)

            self.m2.setVoltageLimit(6)
            self.m2.setPIDs('vel', 2, 20, R=200, F=0.01)
            self.m2.setPIDs('angle', 30, D=4, R=125, F=0.01)

            self.m3.setVoltageLimit(3)
            self.m3.setPIDs('vel', .6, 20, F=0.01)
            self.m3.setPIDs('angle', 20, D=3, R=100, F=0.01)
        except KeyError:
            raise NotImplementedError(
                'A serial connection could not be established with at least one motor.')

    def loadMotors(self):
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
        except FileNotFoundError:
            self.app.calibrateWizardStep1()

    def motorsEnabled(self, value: bool):
        f = Motor.enable if value else Motor.disable
        for motor in self.motors.values():
            f(motor)
        self.app.motorsEnabledVar.set(value)

    @staticmethod
    def autoCalibrate(motor: Motor, voltage: float = 3, speed: float = 1, zeroSpeed: float = 0.1) -> tuple[float, float, float]:
        low, high = 0, 0

        motor.setVoltageLimit(voltage)
        motor.setControlMode('velocity')
        motor.move(-speed)
        motor.enable()

        sleep(1)

        while (v := motor.velocity) is not None and abs(v) > zeroSpeed:
            # print(v)
            sleep(.1)

        motor.move(0)

        if (p := motor.position) is not None:
            low = p

        motor.move(speed)

        sleep(1)

        while (v := motor.velocity) is not None and abs(v) > zeroSpeed:
            # print(v)
            sleep(.1)

        motor.move(0)

        if (p := motor.position) is not None:
            high = p

        motor.offset = (low+high)/2
        motor.setControlMode('angle')
        motor.move(0)

        return low, high, motor.offset

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

        if (p := motor.position) is not None:
            print(p)
            if low <= p <= high:
                motor.offset = center
            elif p < low:
                motor.offset = center - 2*math.pi
            else:
                motor.offset = center + 2*math.pi

            motor.setControlMode('angle')
            motor.move(0)
            motor.enable()

        else:
            print(f'Motor {motor.m_id} disconnected.')

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
        print(f'Homing motor {motor.m_id}')

        angle = 0

        motor.setControlMode('torque')
        motor.move(voltage)
        motor.enable()

        sleep(1)

        while (v := motor.velocity) is not None and abs(v) > zeroSpeed:
            # print(v)
            sleep(.1)

        motor.move(0)

        if (p := motor.position) is not None:
            angle = p

        if active:
            motor.offset = angle
            motor.setControlMode('angle')
            motor.move(centerOffset)
        else:
            motor.disable()

        return angle

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

    def jog(self, **kwargs):
        self.m2.move(kwargs['t1'])
        # if (p := self.m2.position) is not None:
        #     self.m4.move(kwargs['r']-p)
        self.m4.move(kwargs['r']-kwargs['t1'])

        self.m3.move(kwargs['t2'])
        self.m1.move(kwargs['z'])
        if 'e' in kwargs:
            self.endEffector.move(kwargs['e'])

    def smoothMove(self, duration, timeout=1, epsilon=0.1, **end) -> None:
        """
        Smoothly move the motors to a target position.

        This function is intended to be launched in a thread.
        """

        if (t1 := self.m2.position) is not None and (t2 := self.m3.position) is not None and (z := self.m1.position) is not None and (r := self.m4.position) is not None:
            start = {'t1': t1, 't2': t2, 'z': z, 'r': r+t1}
        else:
            raise NotImplementedError(
                'Unable to retreive motor positions for smooth move')

        self.jog(**start, e=end['e'])
        startTime = time()
        while (t := time() - startTime) < duration:
            self.jog(**{axis: bezier(0, start[axis], duration/2, start[axis],
                                     duration/2, end[axis], duration, end[axis], t) for axis in start})

        startTime = time()
        while time() - startTime < timeout:
            sleep(0.1)
            if (p1 := self.m2.position) is not None and (p2 := self.m3.position) is not None and (p3 := self.m1.position) is not None and (p4 := self.m4.position) is not None:
                if abs(end['t1']-p1) < epsilon and abs(end['t2']-p2) < epsilon and abs(end['z']-p3) < epsilon and abs(end['r']-p4-p1) < epsilon:
                    break
            else:
                raise NotImplementedError('Unable to confirm succesful jog.')
        else:
            raise NotImplementedError(
                'Motors could not reach target position in the alloted time.')


class Popup(tk.Toplevel):
    def __init__(self, parent, title=None):
        tk.Toplevel.__init__(self, parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

    def destroy(self):
        self.grab_release()
        tk.Toplevel.destroy(self)

    def center(self):
        self.update()
        w = self.winfo_width()
        h = self.winfo_height()
        wr = self.master.winfo_width()
        hr = self.master.winfo_height()
        x = self.master.winfo_rootx() + wr//2 - w//2
        y = self.master.winfo_rooty() + hr//2 - h//2

        self.geometry(f'+{x}+{y}')


class Application(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.pack(fill='both', expand=True)

        # root.bind('<Up>', lambda _: self.updateTargets(
        #     y=self.targetYVar.get()+0.1))
        # root.bind('<Down>', lambda _: self.updateTargets(
        #     y=self.targetYVar.get()-0.1))
        # root.bind('<Left>', lambda _: self.updateTargets(
        #     x=self.targetXVar.get()+0.1))
        # root.bind('<Right>', lambda _: self.updateTargets(
        #     x=self.targetXVar.get()-0.1))
        # root.bind('w', lambda _: self.updateTargets(
        #     z=self.targetZVar.get()+0.1))
        # root.bind('s', lambda _: self.updateTargets(
        #     z=self.targetZVar.get()-0.1))
        # root.bind('a', lambda _: self.updateTargets(
        #     r=self.targetRVar.get()+0.1))
        # root.bind('d', lambda _: self.updateTargets(
        #     r=self.targetRVar.get()-0.1))
        # root.bind('q', lambda _: self.updateTargets(
        #     e=self.targetEVar.get()+1))
        # root.bind('e', lambda _: self.updateTargets(
        #     e=self.targetEVar.get()-1))

        self.moveDurationVar = tk.DoubleVar()
        self.moveDurationVar.set(2)
        self.motorsEnabledVar = tk.BooleanVar()
        self.motorsEnabledVar.set(True)

        self.initPopup = tk.Toplevel(self)
        self.initPopup.geometry("500x100")
        self.initPopup.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(self.initPopup, text="Initializing...").pack(side='top')

        progress_bar = ttk.Progressbar(
            self.initPopup, mode='indeterminate', value=1)
        progress_bar.pack(fill='x', expand=1, side='bottom', padx=10, pady=10)

        # Initialize Up Robot Arm
        self.robotarm = RobotArm(self)
        # Comment out for GUI work
        Thread(target=self.initRobotArm, daemon=True).start()

    def initRobotArm(self):
        self.robotarm.loadMotors()
        self.initPopup.destroy()
        self.createWidgets()

    def createWidgets(self):
        # Menubar
        menubar = tk.Menu(self)
        fileMenu = tk.Menu(menubar, tearoff=0)
        toolsMenu = tk.Menu(menubar, tearoff=0)
        motorMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=fileMenu)
        menubar.add_cascade(label='Tools', menu=toolsMenu)
        fileMenu.add_command(label='Load Job', command=lambda: Thread(
            target=self.loadJob).start())
        fileMenu.add_command(label='Save Job')
        toolsMenu.add_command(label='Record Job')
        toolsMenu.add_cascade(
            label='Motors', menu=motorMenu)
        toolsMenu.add_command(
            label='Calibration Wizard', command=self.calibrateWizardStep1)
        motorMenu.add_checkbutton(
            label='Enable', variable=self.motorsEnabledVar, command=lambda: self.robotarm.motorsEnabled(self.motorsEnabledVar.get()))
        motorMenu.add_command(
            label='Configure...', command=self.configureMotorsPanel)
        root.config(menu=menubar)

        # Inside of Self
        r = 0
        self.controlFrame = ttk.Frame(self)
        self.controlFrame.pack(side='left', fill='both', expand=True)

        # Inside of ControlFrame
        r, c = 0, 0

        sliderFrame = ttk.Frame(self.controlFrame)
        sliderFrame.grid(row=r, column=c, sticky='WE')

        r += 1

        tk.Button(self.controlFrame, text='Emergency Stop', fg='#F00000',
                  command=lambda: self.robotarm.motorsEnabled(False)).grid(row=r, column=c, sticky='W', padx=5, pady=5)

        # Inside of SliderFrame
        r = 0

        ttk.Label(sliderFrame, text='Axis Motors', font='Helvetica 16 bold').grid(
            row=r, column=0, sticky='W', padx=5, pady=5)
        ttk.Separator(sliderFrame, orient='horizontal').grid(
            sticky='WE', columnspan=3, padx=5, pady=5)

        r += 2

        self.targetXVar = tk.DoubleVar()
        self.targetXVar.set(15)
        self.targetXLabel = ttk.Label(sliderFrame, text='Target X:')
        self.targetXLabel.grid(row=r, padx=5)

        self.targetXEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetXVar, width=5)
        self.targetXEntry.grid(row=r, column=1, padx=5)
        self.targetXEntry.bind('<Return>', lambda _: Thread(
            target=self.jog, daemon=True).start())

        self.targetXSlider = ttk.Scale(sliderFrame, variable=self.targetXVar, command=lambda x: self.updateTargets(
            x=round(float(x), 2)), from_=0, to=30, orient='horizontal')
        self.targetXSlider.grid(row=r, column=2, padx=5)

        r += 1

        self.targetYVar = tk.DoubleVar()
        self.targetYLabel = ttk.Label(sliderFrame, text='Target Y:')
        self.targetYLabel.grid(row=r, padx=5)

        self.targetYEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetYVar, width=5)
        self.targetYEntry.grid(row=r, column=1, padx=5)
        self.targetYEntry.bind('<Return>', lambda _: Thread(
            target=self.jog, daemon=True).start())

        self.targetYSlider = ttk.Scale(sliderFrame, variable=self.targetYVar, command=lambda y: self.updateTargets(
            y=round(float(y), 2)), from_=-30, to=30, orient='horizontal')
        self.targetYSlider.grid(row=r, column=2, padx=5)

        r += 1

        self.targetZVar = tk.DoubleVar()
        self.targetZVar.set(45)
        self.targetZLabel = ttk.Label(sliderFrame, text='Target Z:')
        self.targetZLabel.grid(row=r, padx=5)

        self.targetZEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetZVar, width=5)
        self.targetZEntry.grid(row=r, column=1, padx=5)
        self.targetZEntry.bind('<Return>', lambda _: Thread(
            target=self.jog, daemon=True).start())

        self.targetZSlider = ttk.Scale(sliderFrame, variable=self.targetZVar, command=lambda z: self.updateTargets(
            z=round(float(z), 2)), from_=0, to=90, orient='horizontal')
        self.targetZSlider.grid(row=r, column=2, padx=5)

        r += 1

        self.targetRVar = tk.DoubleVar()
        self.targetRLabel = ttk.Label(sliderFrame, text='Target R:')
        self.targetRLabel.grid(row=r, padx=5)

        self.targetREntry = ttk.Entry(
            sliderFrame, textvariable=self.targetRVar, width=5)
        self.targetREntry.grid(row=r, column=1, padx=5)
        self.targetREntry.bind('<Return>', lambda _: Thread(
            target=self.jog, daemon=True).start())

        self.targetRSlider = ttk.Scale(sliderFrame, variable=self.targetRVar, command=lambda r: self.updateTargets(
            r=round(float(r), 2)), from_=-1.57, to=1.57, orient='horizontal')
        self.targetRSlider.grid(row=r, column=2, padx=5)

        r += 1

        ttk.Label(sliderFrame, text='End Effector', font='Helvetica 16 bold').grid(
            row=r, column=0, sticky='W', padx=5, pady=5)
        ttk.Separator(sliderFrame, orient='horizontal').grid(
            sticky='WE', columnspan=3, padx=5, pady=5)

        r += 2

        self.targetEVar = tk.IntVar()
        self.targetEVar.set(sum(self.robotarm.endEffector.valueRange)//2)
        self.targetELabel = ttk.Label(sliderFrame, text='Target E:')
        self.targetELabel.grid(row=r, padx=5)

        self.targetEEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetEVar, width=5)
        self.targetEEntry.grid(row=r, column=1, padx=5)
        self.targetEEntry.bind('<Return>', lambda _: Thread(
            target=self.jog, daemon=True).start())

        self.targetESlider = ttk.Scale(sliderFrame, variable=self.targetEVar, command=lambda e: self.updateTargets(
            e=round(float(e))), from_=self.robotarm.endEffector.valueRange[0], to=self.robotarm.endEffector.valueRange[1], orient='horizontal')
        self.targetESlider.grid(row=r, column=2, padx=5)

        r += 1

        self.handPosVar = tk.BooleanVar()
        self.handPosToggle = ttk.Checkbutton(
            sliderFrame, variable=self.handPosVar, text='Hand Position', command=lambda: Thread(target=self.handPositioning, daemon=True).start())
        self.handPosToggle.grid(row=r, column=0, sticky='W', padx=5, pady=5)

        self.realtimeVar = tk.BooleanVar()
        self.realtimeToggle = ttk.Checkbutton(
            sliderFrame, variable=self.realtimeVar, text='Realtime')
        self.realtimeToggle.grid(row=r, column=1, sticky='W', padx=5, pady=5)

        self.jogButton = ttk.Button(sliderFrame, text='Jog',
                                    command=self.jog)
        self.jogButton.grid(row=r, column=2, padx=5, pady=5)

        r += 1

    def calibrateWizardStep1(self):
        self.popup = Popup(self)
        self.popup.geometry('400x400')
        self.popup.title('Calibration Wizard')
        self.popup.center()

        self.contentFrame = ttk.Frame(self.popup)
        self.contentFrame.pack(side='top', fill='both', expand=True)
        self.contentFrame.grid_rowconfigure(0, weight=1)
        self.contentFrame.grid_rowconfigure(10, weight=1)
        self.contentFrame.grid_columnconfigure(0, weight=1)
        self.contentFrame.grid_columnconfigure(2, weight=1)

        buttons = ttk.Frame(self.popup)
        buttons.pack(side='bottom', fill='x')

        self.continueButton = ttk.Button(buttons, text='Continue', command=lambda: Thread(
            target=self.calibrateWizardStep2, daemon=True).start())
        self.continueButton.pack(side='right')
        self.cancelButton = ttk.Button(buttons, text='Cancel',
                                       command=self.popup.destroy)
        self.cancelButton.pack(side='right')

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 2', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)

        ttk.Label(self.contentFrame, text="""Motor 2 requires manual calibration.
The motor will start slowly rotating left.
Let the motor spin as far as you are comfortable
and stop it with your hand when you are ready.
Click continue to begin.
                     """
                  ).grid(column=c, sticky='W', padx=5, pady=5)

        self.robotarm.motorsEnabled(False)
        self.robotarm.m2.offset = 0
        self.robotarm.m3.offset = 0
        self.robotarm.m4.offset = 0

    def calibrateWizardStep2(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        low = self.robotarm.singleEndedHome(
            self.robotarm.m2,
            voltage=-12,
            zeroSpeed=0.1,
            active=False
        )

        with open('config/m2', 'w') as f:
            f.write(f'{low}\n')

        self.continueButton['command'] = self.calibrateWizardStep3
        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Continue'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 2', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)

        ttk.Label(self.contentFrame, text="""Now the motor will rotate to the right.
Let the motor spin as far as you are comfortable
and stop it with your hand when you are ready.
Click continue to begin.
                     """
                  ).grid(column=c, sticky='W', padx=5, pady=5)

    def calibrateWizardStep3(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        high = self.robotarm.singleEndedHome(
            self.robotarm.m2,
            voltage=12,
            zeroSpeed=0.1,
            active=False
        )

        with open('config/m2', 'a') as f:
            f.write(f'{high}\n')

        self.continueButton['command'] = self.calibrateWizardStep4
        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Continue'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 2', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)

        ttk.Label(self.contentFrame, text="""Position the motor where you would like the center to be.
Click continue to begin.
                     """
                  ).grid(column=c, sticky='W', padx=5, pady=5)

    def calibrateWizardStep4(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.robotarm.m2

        if (p := self.robotarm.m2.position) is not None:
            motor.offset = center = p
        else:
            self.wizardFailed()
            return

        with open('config/m2', 'a') as f:
            f.write(f'{center}\n')

        motor.setControlMode('angle')
        motor.move(0)
        motor.enable()

        self.continueButton['command'] = self.calibrateWizardStep5
        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Continue'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 4', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)

        ttk.Label(self.contentFrame, text="""Position the motor where you would like the left extreme to be.
Click continue to begin."""
                  ).grid(column=c, sticky='W', padx=5, pady=5)

    def calibrateWizardStep5(self, word='left'):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.robotarm.m4

        if (p := motor.position) is not None:
            value = p
        else:
            self.wizardFailed()
            return

        with open('config/m4', 'w' if word == 'left' else 'a') as f:
            f.write(f'{value}\n')

        if word != 'center':
            if word == 'left':
                self.continueButton['command'] = lambda: self.calibrateWizardStep5(
                    'right')
                word = 'right'
            elif word == 'right':
                self.continueButton['command'] = lambda: self.calibrateWizardStep5(
                    'center')
                word = 'center'
            word += ' extreme'

        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Continue'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        if word == 'center':
            self.robotarm.m4.offset = value
            self.calibrateWizardStep6()
            return

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 4', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)
        ttk.Label(self.contentFrame, text=f"""Position the motor where you would like the {word} to be.
Click continue to begin."""
                  ).grid(column=c, sticky='W', padx=5, pady=5)

    def calibrateWizardStep6(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.robotarm.m4

        motor.setControlMode('angle')
        motor.move(0)
        motor.enable()

        self.continueButton['command'] = self.calibrateWizardStep7
        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Continue'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 3', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)
        ttk.Label(self.contentFrame, text='Motor 3 can self calibrate,\nclick Continue to begin.'
                  ).grid(column=c, sticky='W', padx=5, pady=5)

    def calibrateWizardStep7(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        with open('config/m3', 'w') as f:
            for num in self.robotarm.autoCalibrate(self.robotarm.m3, speed=2):
                f.write(f'{num}\n')

        self.cancelButton.destroy()
        self.continueButton['command'] = lambda: self.popup.destroy()
        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Finish'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Calibration Complete', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)

        ttk.Label(self.contentFrame, text='Click finish to close this window.'
                  ).grid(column=c, sticky='W', padx=5, pady=5)

        self.robotarm.m1.enable()

    def wizardFailed(self):
        raise NotImplementedError("Calibration wizard failed.")

    def handPositioning(self):
        """
        Release motors to allow for hand movement.
        Update motor positions until hand position mode is disabled.
        Re-enable motors.

        This function is intended to be launched in a thread.
        """
        self.robotarm.m2.disable()
        self.robotarm.m3.disable()
        self.robotarm.m4.disable()

        while self.handPosVar.get():
            if (t1 := self.robotarm.m2.position) is not None and (t2 := self.robotarm.m3.position) is not None and (r := self.robotarm.m4.position) is not None:
                x, y = self.robotarm.polarToCartesian(t1, t2)
                self.targetXVar.set(round(x, 2))
                self.targetYVar.set(round(y, 2))
                self.targetRVar.set(round(r, 2))
            else:
                return

        self.robotarm.motorsEnabled(True)
        self.jog()

    def configureMotorsPanel(self):
        popup = Popup(self, 'Motors')

        topFrame = ttk.Frame(popup)
        topFrame.pack(side='top')

        bottomFrame = ttk.Frame(popup)
        bottomFrame.pack(side='bottom', fill='x')

        notebook = ttk.Notebook(popup)
        notebook.pack(side='bottom', fill='both', expand=True)

        infoFrame = ttk.Frame(notebook)
        infoFrame.pack(fill='both', expand=True)
        infoFrame.grid_rowconfigure(0, weight=1)
        infoFrame.grid_rowconfigure(10, weight=1)
        infoFrame.grid_columnconfigure(0, weight=1)
        infoFrame.grid_columnconfigure(3, weight=1)

        configFrame = ttk.Frame(notebook)
        configFrame.pack(fill='both', expand=True)
        configFrame.grid_rowconfigure(0, weight=1)
        configFrame.grid_rowconfigure(10, weight=1)
        configFrame.grid_columnconfigure(0, weight=1)
        configFrame.grid_columnconfigure(3, weight=1)

        pidFrame = ttk.Frame(notebook)
        pidFrame.pack(fill='both', expand=True)

        consoleFrame = ttk.Frame(notebook)
        consoleFrame.pack(fill='both', expand=True)

        notebook.add(infoFrame, text='Info')
        notebook.add(configFrame, text='Config')
        notebook.add(pidFrame, text='PIDs')
        notebook.add(consoleFrame, text='Console')

        s = tk.StringVar()
        # motorSelect = ttk.OptionMenu(
        #     topFrame, s, f'Motor {list(self.robotarm.motors.keys())[0]}', *[f'Motor {id}' for id in self.robotarm.motors])
        motorSelect = ttk.OptionMenu(
            topFrame, s, 'Motor 1', 'Motor 1', 'Motor 2', 'Motor 3', 'Motor 4', command=self.selectMotor)
        motorSelect.pack(side='left')
        ttk.Label(topFrame, text='❌').pack(side='left')

        ttk.Button(bottomFrame, text='Apply',
                   command=popup.destroy).pack(side='right')

        ttk.Button(bottomFrame, text='Cancel',
                   command=popup.destroy).pack(side='right')

        ttk.Button(bottomFrame, text='Ok',
                   command=popup.destroy).pack(side='right')

        # Info
        r = 1
        c = 1

        ttk.Label(infoFrame, text='USB',
                  font='Helvitica 12 bold').grid(row=r, column=c, sticky='W')
        ttk.Separator(infoFrame, orient='horizontal').grid(
            column=c, sticky='WE', columnspan=2)

        r += 2

        ttk.Label(infoFrame, text='Active:').grid(row=r, column=c, sticky='W')
        ttk.Label(infoFrame, text='❌').grid(
            row=r, column=c+1, sticky='W')

        r += 1

        ttk.Label(infoFrame, text='Port:').grid(row=r, column=c, sticky='W')
        ttk.Label(infoFrame, text='？', foreground='orange').grid(
            row=r, column=c+1, sticky='W')

        r += 1

        ttk.Label(infoFrame, text='Power',
                  font='Helvitica 12 bold').grid(row=r, column=c, sticky='W')
        ttk.Separator(infoFrame, orient='horizontal').grid(
            column=c, sticky='WE', columnspan=2)

        r += 2

        ttk.Label(infoFrame, text='External Supply:').grid(
            row=r, column=c, sticky='W')
        ttk.Label(infoFrame, text='？', foreground='orange').grid(
            row=r, column=c+1, sticky='W')

        ttk.Label(infoFrame, text='DRV8316',
                  font='Helvitica 12 bold').grid(column=c, sticky='W')
        ttk.Separator(infoFrame, orient='horizontal').grid(
            column=c, sticky='WE', columnspan=2)

        r += 3

        ttk.Label(infoFrame, text='Status:').grid(row=r, column=c, sticky='W')
        ttk.Label(infoFrame, text='？', foreground='orange').grid(
            row=r, column=c+1, sticky='W')

        # Config
        r = 1
        c = 1

        self.motorEnabledVar = tk.BooleanVar()

        ttk.Checkbutton(configFrame, variable=self.motorEnabledVar,
                        text='Enabled').grid(row=r, column=c, sticky='W')

        r += 1

        self.voltageLimitVar = tk.DoubleVar()

        ttk.Label(configFrame, text='Voltage Limit:').grid(
            row=r, column=c, sticky='W')

        ttk.Entry(configFrame, textvariable=self.voltageLimitVar,
                  width=4).grid(row=r, column=c+1, sticky='W')

        r += 1

        self.velocityLimitVar = tk.DoubleVar()

        ttk.Label(configFrame, text='Velocity Limit:').grid(
            row=r, column=c, sticky='W')

        ttk.Entry(configFrame, textvariable=self.velocityLimitVar,
                  width=4).grid(row=r, column=c+1, sticky='W')

        r += 1

        self.controlModeVar = tk.DoubleVar()

        ttk.Label(configFrame, text='Control Mode:').grid(
            row=r, column=c, sticky='W')

        ttk.OptionMenu(configFrame, self.controlModeVar, 'torque', 'torque',
                       'velocity', 'angle').grid(row=r, column=c+1, sticky='W')

        # PIDs

        # Center
        popup.center()

    def selectMotor(self, motor):
        raise NotImplementedError(
            "This should somehow select what motor is being configured by the motor configuration panel.")

    def loadJob(self):
        fileName = fd.askopenfilename(
            title='Select Job File',
            filetypes=[('GCode', '*.gcode')],
        )

        self.jobPopup = tk.Toplevel(self)
        self.jobPopup.geometry("500x100")
        self.jobPopup.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(self.jobPopup, text="Running Job").pack(side='top')
        progress = 0
        progressVar = tk.IntVar()

        self.realtimeVar.set(False)

        with open(fileName, 'r') as f:
            lines = f.readlines()
            progress_bar = ttk.Progressbar(
                self.jobPopup, variable=progressVar, length=500, maximum=len(lines))
            progress_bar.pack(fill='x', expand=1,
                              side='bottom', padx=10, pady=10)
            for line in lines:
                for argument, value in readGcodeLine(line):
                    if argument == 'X':
                        self.targetXVar.set(value)
                    elif argument == 'Y':
                        self.targetYVar.set(value)
                    elif argument == 'Z':
                        self.targetZVar.set(value)
                    elif argument == 'R':
                        self.targetRVar.set(value)
                    elif argument == 'E':
                        self.targetEVar.set(int(value))
                    elif argument == 'D':
                        self.moveDurationVar.set(value)
                self.jog()
                progress += 1
                progressVar.set(progress)

        self.jobPopup.destroy()

    def updateTargets(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None, r: Optional[float] = None, e: Optional[int] = None):
        digits = 3

        if x is not None:
            self.targetXVar.set(round(x, digits))
        if y is not None:
            self.targetYVar.set(round(y, digits))
        if z is not None:
            self.targetZVar.set(round(z, digits))
        if r is not None:
            self.targetRVar.set(round(r, digits))
        if e is not None:
            self.targetEVar.set(e)

        if self.realtimeVar.get():
            self.jog()

    def jog(self):
        timeout = 5
        epsilon = 0.1

        self.jogButton['state'] = 'disabled'

        t1, t2 = self.robotarm.cartesianToDualPolar(
            self.targetXVar.get(), self.targetYVar.get())
        z = self.targetZVar.get()
        r = self.targetRVar.get()
        e = self.targetEVar.get()

        if self.realtimeVar.get():
            self.robotarm.jog(t1=t1, t2=t2, z=z, r=r, e=e)
        else:
            self.robotarm.smoothMove(
                self.moveDurationVar.get(), timeout=timeout, epsilon=epsilon, t1=t1, t2=t2, z=z, r=r, e=e)

        self.jogButton['state'] = 'normal'

    def on_close(self):
        self.robotarm.motorsEnabled(False)
        self.robotarm.endEffector.move(10)
        root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Robot Arm')
    app = Application(root)
    root.eval('tk::PlaceWindow . center')
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
