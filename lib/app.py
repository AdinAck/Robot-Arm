from threading import Thread

from lib.system import System
from lib.gcode import readGcodeLine

import tkinter as tk
from tkinter import filedialog as fd
import tkinter.ttk as ttk

from typing import Optional


class Application(ttk.Frame):
    system: System = System()

    def __init__(self, master):
        ttk.Frame.__init__(self, master)
        self.root = master
        self.pack(fill="both", expand=True)

        self.moveDurationVar = tk.DoubleVar()
        self.moveDurationVar.set(2)
        self.motorsEnabledVar = tk.BooleanVar()
        self.motorsEnabledVar.set(True)

        self.initPopup = tk.Toplevel(self)
        self.initPopup.geometry("500x100")
        self.initPopup.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(self.initPopup, text="Initializing...").pack(side="top")

        progress_bar = ttk.Progressbar(self.initPopup, mode="indeterminate", value=1)
        progress_bar.pack(fill="x", expand=1, side="bottom", padx=10, pady=10)

        # Initialize Up Robot Arm
        self.system = System()
        Thread(target=self.initSystem, daemon=True).start()

        # Initialize first-party widgets
        from widgets.builtin.calibrationWizard import CalibrationWizard
        from widgets.builtin.configureMotors import ConfigureMotors
        from widgets.builtin.visual import Visual

        self.calibrationWizard = CalibrationWizard(self)
        self.configureationPanel = ConfigureMotors(self)
        self.visual = Visual(self)

    def initSystem(self):
        self.system.loadMotors()
        self.initPopup.destroy()
        self.createWidgets()

    def createWidgets(self):
        # Menubar
        menubar = tk.Menu(self)
        fileMenu = tk.Menu(menubar, tearoff=0)
        toolsMenu = tk.Menu(menubar, tearoff=0)
        motorMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=fileMenu)
        menubar.add_cascade(label="Tools", menu=toolsMenu)
        fileMenu.add_command(
            label="Load Job", command=lambda: Thread(target=self.loadJob).start()
        )
        fileMenu.add_command(label="Save Job")
        toolsMenu.add_command(label="Record Job")
        toolsMenu.add_cascade(label="Motors", menu=motorMenu)
        toolsMenu.add_command(
            label="Calibration Wizard", command=self.calibrationWizard.show
        )
        toolsMenu.add_command(label="Visual", command=self.visual.show)
        motorMenu.add_checkbutton(
            label="Enable",
            variable=self.motorsEnabledVar,
            command=lambda: self.motorsEnabled(self.motorsEnabledVar.get()),
        )
        motorMenu.add_command(
            label="Configure...", command=self.configureationPanel.show
        )
        self.root.config(menu=menubar)

        # Inside of Self
        r = 0
        self.controlFrame = ttk.Frame(self)
        self.controlFrame.pack(side="left", fill="both", expand=True)

        # Inside of ControlFrame
        r, c = 0, 0

        sliderFrame = ttk.Frame(self.controlFrame)
        sliderFrame.grid(row=r, column=c, sticky="WE")

        r += 1

        tk.Button(
            self.controlFrame,
            text="Emergency Stop",
            fg="#F00000",
            command=lambda: self.motorsEnabled(False),
        ).grid(row=r, column=c, sticky="W", padx=5, pady=5)

        # Inside of SliderFrame
        r = 0

        ttk.Label(sliderFrame, text="Axis Motors", font="Helvetica 16 bold").grid(
            row=r, column=0, sticky="W", padx=5, pady=5
        )
        ttk.Separator(sliderFrame, orient="horizontal").grid(
            sticky="WE", columnspan=3, padx=5, pady=5
        )

        r += 2

        self.targetXVar = tk.DoubleVar()
        self.targetXVar.set(15)
        self.targetXLabel = ttk.Label(sliderFrame, text="Target X:")
        self.targetXLabel.grid(row=r, padx=5)

        self.targetXEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetXVar, width=5
        )
        self.targetXEntry.grid(row=r, column=1, padx=5)
        self.targetXEntry.bind(
            "<Return>", lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.targetXSlider = ttk.Scale(
            sliderFrame,
            variable=self.targetXVar,
            command=lambda x: self.updateTargets(x=round(float(x), 2)),
            from_=0,
            to=30,
            orient="horizontal",
        )
        self.targetXSlider.grid(row=r, column=2, padx=5)

        r += 1

        self.targetYVar = tk.DoubleVar()
        self.targetYLabel = ttk.Label(sliderFrame, text="Target Y:")
        self.targetYLabel.grid(row=r, padx=5)

        self.targetYEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetYVar, width=5
        )
        self.targetYEntry.grid(row=r, column=1, padx=5)
        self.targetYEntry.bind(
            "<Return>", lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.targetYSlider = ttk.Scale(
            sliderFrame,
            variable=self.targetYVar,
            command=lambda y: self.updateTargets(y=round(float(y), 2)),
            from_=-30,
            to=30,
            orient="horizontal",
        )
        self.targetYSlider.grid(row=r, column=2, padx=5)

        r += 1

        self.targetZVar = tk.DoubleVar()
        self.targetZVar.set(45)
        self.targetZLabel = ttk.Label(sliderFrame, text="Target Z:")
        self.targetZLabel.grid(row=r, padx=5)

        self.targetZEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetZVar, width=5
        )
        self.targetZEntry.grid(row=r, column=1, padx=5)
        self.targetZEntry.bind(
            "<Return>", lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.targetZSlider = ttk.Scale(
            sliderFrame,
            variable=self.targetZVar,
            command=lambda z: self.updateTargets(z=round(float(z), 2)),
            from_=0,
            to=90,
            orient="horizontal",
        )
        self.targetZSlider.grid(row=r, column=2, padx=5)

        r += 1

        self.targetRVar = tk.DoubleVar()
        self.targetRLabel = ttk.Label(sliderFrame, text="Target R:")
        self.targetRLabel.grid(row=r, padx=5)

        self.targetREntry = ttk.Entry(
            sliderFrame, textvariable=self.targetRVar, width=5
        )
        self.targetREntry.grid(row=r, column=1, padx=5)
        self.targetREntry.bind(
            "<Return>", lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.targetRSlider = ttk.Scale(
            sliderFrame,
            variable=self.targetRVar,
            command=lambda r: self.updateTargets(r=round(float(r), 2)),
            from_=-1.57,
            to=1.57,
            orient="horizontal",
        )
        self.targetRSlider.grid(row=r, column=2, padx=5)

        r += 1

        ttk.Label(sliderFrame, text="End Effector", font="Helvetica 16 bold").grid(
            row=r, column=0, sticky="W", padx=5, pady=5
        )
        ttk.Separator(sliderFrame, orient="horizontal").grid(
            sticky="WE", columnspan=3, padx=5, pady=5
        )

        r += 2

        self.targetEVar = tk.IntVar()
        self.targetEVar.set(sum(self.system.endEffector.valueRange) // 2)
        self.targetELabel = ttk.Label(sliderFrame, text="Target E:")
        self.targetELabel.grid(row=r, padx=5)

        self.targetEEntry = ttk.Entry(
            sliderFrame, textvariable=self.targetEVar, width=5
        )
        self.targetEEntry.grid(row=r, column=1, padx=5)
        self.targetEEntry.bind(
            "<Return>", lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.targetESlider = ttk.Scale(
            sliderFrame,
            variable=self.targetEVar,
            command=lambda e: self.updateTargets(e=round(float(e))),
            from_=self.system.endEffector.valueRange[0],
            to=self.system.endEffector.valueRange[1],
            orient="horizontal",
        )
        self.targetESlider.grid(row=r, column=2, padx=5)

        r += 1

        self.handPosVar = tk.BooleanVar()
        self.handPosToggle = ttk.Checkbutton(
            sliderFrame,
            variable=self.handPosVar,
            text="Hand Position",
            command=lambda: Thread(target=self.handPositioning, daemon=True).start(),
        )
        self.handPosToggle.grid(row=r, column=0, sticky="W", padx=5, pady=5)

        self.realtimeVar = tk.BooleanVar()
        self.realtimeToggle = ttk.Checkbutton(
            sliderFrame, variable=self.realtimeVar, text="Realtime"
        )
        self.realtimeToggle.grid(row=r, column=1, sticky="W", padx=5, pady=5)

        self.jogButton = ttk.Button(sliderFrame, text="Jog", command=self.jog)
        self.jogButton.grid(row=r, column=2, padx=5, pady=5)

        r += 1

    def handPositioning(self):
        """
        Release motors to allow for hand movement.
        Update motor positions until hand position mode is disabled.
        Re-enable motors.
        Jog.

        This function is intended to be launched in a thread.
        """
        self.system.m_inner_rot.disable()
        self.system.m_outer_rot.disable()
        self.system.m_end_rot.disable()

        self.realtimeVar.set(True)

        while self.handPosVar.get():
            t1, t2, _, r = self.system.getAllPos()
            x, y = self.system.polarToCartesian(t1, t2)
            self.targetXVar.set(round(x, 2))
            self.targetYVar.set(round(y, 2))
            self.targetRVar.set(round(r + t1, 2))

        self.realtimeVar.set(False)
        self.motorsEnabled(True)
        self.jog()

    def loadJob(self):
        fileName = fd.askopenfilename(
            title="Select Job File",
            filetypes=[("GCode", "*.gcode")],
        )

        self.jobPopup = tk.Toplevel(self)
        self.jobPopup.geometry("500x100")
        self.jobPopup.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(self.jobPopup, text="Running Job").pack(side="top")
        progress = 0
        progressVar = tk.IntVar()

        self.realtimeVar.set(False)

        with open(fileName, "r") as f:
            lines = f.readlines()
            progress_bar = ttk.Progressbar(
                self.jobPopup, variable=progressVar, length=500, maximum=len(lines)
            )
            progress_bar.pack(fill="x", expand=1, side="bottom", padx=10, pady=10)
            for line in lines:
                for argument, value in readGcodeLine(line):
                    if argument == "X":
                        self.targetXVar.set(value)
                    elif argument == "Y":
                        self.targetYVar.set(value)
                    elif argument == "Z":
                        self.targetZVar.set(value)
                    elif argument == "R":
                        self.targetRVar.set(value)
                    elif argument == "E":
                        self.targetEVar.set(int(value))
                    elif argument == "D":
                        self.moveDurationVar.set(value)
                self.jog()
                progress += 1
                progressVar.set(progress)

        self.jobPopup.destroy()

    def updateTargets(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        r: Optional[float] = None,
        e: Optional[int] = None,
    ):
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

        self.jogButton["state"] = "disabled"

        t1, t2 = self.system.cartesianToDualPolar(
            self.targetXVar.get(), self.targetYVar.get()
        )
        z = self.targetZVar.get()
        r = self.targetRVar.get()
        e = self.targetEVar.get()

        if self.realtimeVar.get():
            self.system.jog(t1=t1, t2=t2, z=z, r=r, e=e)
        else:
            self.system.smoothMove(
                self.moveDurationVar.get(),
                timeout=timeout,
                epsilon=epsilon,
                t1=t1,
                t2=t2,
                z=z,
                r=r,
                e=e,
            )

        self.jogButton["state"] = "normal"

    def motorsEnabled(self, value: bool):
        self.system.motorsEnabled(value)
        self.motorsEnabledVar.set(value)

    def on_close(self):
        self.motorsEnabled(False)
        self.system.endEffector.move(10)
        self.root.destroy()
