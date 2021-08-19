import os.path
from threading import Thread
from serial import Serial
from serial.tools.list_ports import comports
from time import sleep
import math
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

    def __init__(self, app):
        self.app = app
        devices = [Motor(str(d.device))
                   for d in comports() if d.description == 'Adafruit Feather M0']

        self.motors = {motor.id: motor for motor in devices}

        self.m1 = self.motors[1]
        self.m2 = self.motors[2]
        self.m3 = self.motors[3]
        self.m4 = self.motors[4]

        self.m2.setVoltageLimit(3)
        self.m2.setPIDs('vel', 2, 20, R=200, F=0.01)
        self.m2.setPIDs('angle', 30, D=5, R=125, F=0.01)

        self.m3.setVoltageLimit(3)
        self.m3.setPIDs('vel', .6, 20, F=0.01)
        self.m3.setPIDs('angle', 20, D=3, R=100, F=0.01)

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

    def disableAll(self):
        for motor in self.motors.values():
            motor.disable()

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
            print(f'Motor {motor.id} disconnected.')

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
        print(f'Homing motor {motor.id}')

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
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

    def destroy(self):
        self.grab_release()
        tk.Toplevel.destroy(self)


class Application(ttk.Frame):
    def __init__(self, master=None):
        ttk.Frame.__init__(self, master)
        self.pack(fill='both', expand=True)

        self.robotarm = RobotArm(self)
        self.robotarm.loadMotors()

        self.controlFrame = ttk.Frame(self)
        self.controlFrame.grid(row=1, column=0, sticky='WE')
        r = 0

        self.motorConfigButton = ttk.Button(
            self.controlFrame, text='Motors...', command=self.configureMotorsPanel)
        self.motorConfigButton.grid(row=r, sticky='E')

        r += 1

        self.realtimeVar = tk.BooleanVar()
        self.realtimeToggle = ttk.Checkbutton(
            self.controlFrame, variable=self.realtimeVar, text='Realtime')
        self.realtimeToggle.grid(row=r, sticky='W')

        r += 1

        self.targetXVar = tk.DoubleVar()
        self.targetXLabel = ttk.Label(self.controlFrame, text='Target X:')
        self.targetXLabel.grid(row=r, sticky='E')

        self.targetXEntry = ttk.Entry(
            self.controlFrame, textvariable=self.targetXVar, width=10)
        self.targetXEntry.grid(row=r, column=1, sticky='W')
        self.targetXEntry.bind('<Return>', lambda _: self.jog())

        self.targetXSlider = ttk.Scale(self.controlFrame, variable=self.targetXVar, command=lambda x: self.updateTargets(
            x=round(float(x), 1)), from_=0, to=30, orient='horizontal')
        self.targetXSlider.grid(row=r, column=2, sticky='W')

        r += 1

        self.targetYVar = tk.DoubleVar()
        self.targetYLabel = ttk.Label(self.controlFrame, text='Target Y:')
        self.targetYLabel.grid(row=r, sticky='E')

        self.targetYEntry = ttk.Entry(
            self.controlFrame, textvariable=self.targetYVar, width=10)
        self.targetYEntry.grid(row=r, column=1, sticky='W')
        self.targetYEntry.bind('<Return>', lambda _: self.jog())

        self.targetYSlider = ttk.Scale(self.controlFrame, variable=self.targetYVar, command=lambda y: self.updateTargets(
            y=round(float(y), 1)), from_=-30, to=30, orient='horizontal')
        self.targetYSlider.grid(row=r, column=2, sticky='W')

        r += 1

        self.targetZVar = tk.DoubleVar()
        self.targetZLabel = ttk.Label(self.controlFrame, text='Target Z:')
        self.targetZLabel.grid(row=r, sticky='E')

        self.targetZEntry = ttk.Entry(
            self.controlFrame, textvariable=self.targetZVar, width=10)
        self.targetZEntry.grid(row=r, column=1, sticky='W')
        self.targetZEntry.bind('<Return>', lambda _: self.jog())

        self.targetZSlider = ttk.Scale(self.controlFrame, variable=self.targetZVar, command=lambda z: self.updateTargets(
            z=round(float(z), 1)), from_=0, to=90, orient='horizontal')
        self.targetZSlider.grid(row=r, column=2, sticky='W')

        r += 1

        self.targetRVar = tk.DoubleVar()
        self.targetRLabel = ttk.Label(self.controlFrame, text='Target R:')
        self.targetRLabel.grid(row=r, sticky='E')

        self.targetREntry = ttk.Entry(
            self.controlFrame, textvariable=self.targetRVar, width=10)
        self.targetREntry.grid(row=r, column=1, sticky='W')
        self.targetREntry.bind('<Return>', lambda _: self.jog())

        self.targetRSlider = ttk.Scale(self.controlFrame, variable=self.targetRVar, command=lambda r: self.updateTargets(
            r=round(float(r), 1)), from_=-1.57, to=1.57, orient='horizontal')
        self.targetRSlider.grid(row=r, column=2, sticky='W')

        self.requiresConnectedMotors = []
        self.assignedPerMotor = []

        # Menubar
        menubar = tk.Menu(self)
        calibrateMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Calibrate', menu=calibrateMenu)
        calibrateMenu.add_command(
            label='Calibration Wizard', command=self.calibrateWizardStep1)
        root.config(menu=menubar)

    def calibrateWizardStep1(self):
        self.popup = Popup(self)
        self.popup.geometry('300x300')
        self.popup.title('Calibration Wizard')

        self.contentFrame = ttk.Frame(self.popup)
        self.contentFrame.pack(side='top', fill='both', expand=True)

        buttons = ttk.Frame(self.popup)
        buttons.pack(side='bottom', fill='x')

        self.continueButton = ttk.Button(buttons, text='Continue', command=lambda: Thread(
            target=self.calibrateWizardStep2).start())
        self.continueButton.pack(side='right')
        self.cancelButton = ttk.Button(buttons, text='Cancel',
                                       command=self.popup.destroy)
        self.cancelButton.pack(side='right')

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 2', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')

        ttk.Label(self.contentFrame, text="""Motor 2 requires manual calibration.
The motor will start slowly rotating left.
Let the motor spin as far as you are comfortable
and stop it with your hand when you are ready.
Click continue to begin.
                     """
                  ).grid(column=c, sticky='W')

        self.robotarm.disableAll()
        for motor in self.robotarm.motors.values():
            motor.offset = 0

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
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')

        ttk.Label(self.contentFrame, text="""Now the motor will rotate to the right.
Let the motor spin as far as you are comfortable
and stop it with your hand when you are ready.
Click continue to begin.
                     """
                  ).grid(column=c, sticky='W')

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
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')

        ttk.Label(self.contentFrame, text="""Position the motor where you would like the center to be.
Click continue to begin.
                     """
                  ).grid(column=c, sticky='W')

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
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')

        ttk.Label(self.contentFrame, text="""Position the motor where you would like the left extreme to be.
Click continue to begin."""
                  ).grid(column=c, sticky='W')

    def calibrateWizardStep5(self, word='left'):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.robotarm.m4

        if (p := motor.position) is not None:
            value = p
        else:
            self.wizardFailed()
            return

        with open('config/m4', 'a') as f:
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
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')
        ttk.Label(self.contentFrame, text=f"""Position the motor where you would like the {word} to be.
Click continue to begin."""
                  ).grid(column=c, sticky='W')

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
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')
        ttk.Label(self.contentFrame, text='Motor 3 can self calibrate,\nclick Continue to begin.'
                  ).grid(column=c, sticky='W')

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
            row=r, column=c, sticky='W')
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='EW')

        ttk.Label(self.contentFrame, text='Click finish to close this window.'
                  ).grid(column=c, sticky='W')

    def wizardFailed(self):
        pass

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
        popup.update()
        w = popup.winfo_width()
        h = popup.winfo_height()
        wr = popup.master.winfo_width()
        hr = popup.master.winfo_height()
        x = popup.master.winfo_rootx() + wr//2 - w//2
        y = popup.master.winfo_rooty() + hr//2 - h//2

        popup.geometry(f'+{x}+{y}')

    def selectMotor(self, motor):
        pass

    def updateTargets(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None, r: Optional[float] = None):
        if x is not None:
            self.targetXVar.set(x)
        if y is not None:
            self.targetYVar.set(y)
        if z is not None:
            self.targetZVar.set(z)
        if r is not None:
            self.targetRVar.set(r)

        self.jog()

    def jog(self):
        t1, t2 = self.robotarm.cartesianToDualPolar(
            self.targetXVar.get(), self.targetYVar.get()
        )

        self.robotarm.m2.move(t1)
        self.robotarm.m4.move(self.targetRVar.get()-t1)
        self.robotarm.m3.move(t2)
        self.robotarm.m1.move(self.targetZVar.get())


if __name__ == '__main__':
    root = tk.Tk()
    root.title('Robot Arm')
    app = Application(root)
    root.eval('tk::PlaceWindow . center')
    app.mainloop()
