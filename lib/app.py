from threading import Thread

from lib.system import System
from lib.gcode import read_gcode_line

import tkinter as tk
from tkinter import filedialog as fd
import tkinter.ttk as ttk

from typing import Optional


class Application(ttk.Frame):
    system: System

    def __init__(self, master):
        ttk.Frame.__init__(self, master)
        self.root = master
        self.pack(fill='both', expand=True)

        self.move_duration_var = tk.DoubleVar()
        self.move_duration_var.set(2)
        self.motors_enabled_var = tk.BooleanVar()
        self.motors_enabled_var.set(True)

        self.init_popup = tk.Toplevel(self)
        self.init_popup.geometry('500x100')
        self.init_popup.protocol('WM_DELETE_WINDOW', lambda: None)
        ttk.Label(self.init_popup, text='Initializing...').pack(side='top')

        progress_bar = ttk.Progressbar(
            self.init_popup, mode='indeterminate', value=1)
        progress_bar.pack(fill='x', expand=1, side='bottom', padx=10, pady=10)

        # Initialize Up Robot Arm
        self.system = System()
        Thread(target=self.init_system, daemon=True).start()

        # Initialize first-party widgets
        from widgets.builtin.calibrationWizard import CalibrationWizard
        from widgets.builtin.configureMotors import ConfigureMotors
        from widgets.builtin.visual import Visual
        from widgets.builtin.hand_tracking import HandTracking

        self.calibration_wizard = CalibrationWizard(self)
        self.configureation_panel = ConfigureMotors(self)
        self.visual = Visual(self)
        self.hand_tracking = HandTracking(self)

    def init_system(self):
        self.system.load_motors()
        self.init_popup.destroy()
        self.create_widgets()

    def create_widgets(self):
        # Menubar
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        tools_menu = tk.Menu(menubar, tearoff=0)
        motor_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=file_menu)
        menubar.add_cascade(label='Tools', menu=tools_menu)
        file_menu.add_command(
            label='Load Job', command=lambda: Thread(target=self.load_job).start()
        )
        file_menu.add_command(label='Save Job')
        tools_menu.add_command(label='Record Job')
        tools_menu.add_cascade(label='Motors', menu=motor_menu)
        tools_menu.add_command(
            label='Calibration Wizard', command=self.calibration_wizard.show
        )
        tools_menu.add_command(label='Visual', command=self.visual.show)
        tools_menu.add_command(label='Hand Tracking',
                               command=self.hand_tracking.show)
        motor_menu.add_checkbutton(
            label='Enable',
            variable=self.motors_enabled_var,
            command=lambda: self.motors_enabled(self.motors_enabled_var.get()),
        )
        motor_menu.add_command(
            label='Configure...', command=self.configureation_panel.show
        )
        self.root.config(menu=menubar)

        # Inside of Self
        r = 0
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(side='left', fill='both', expand=True)

        # Inside of Control_Frame
        r, c = 0, 0

        slider_frame = ttk.Frame(self.control_frame)
        slider_frame.grid(row=r, column=c, sticky='WE')

        r += 1

        tk.Button(
            self.control_frame,
            text='Emergency Stop',
            fg='#F00000',
            command=lambda: self.motors_enabled(False),
        ).grid(row=r, column=c, sticky='W', padx=5, pady=5)

        # Inside of SliderFrame
        r = 0

        ttk.Label(slider_frame, text='Axis Motors', font='Helvetica 16 bold').grid(
            row=r, column=0, sticky='W', padx=5, pady=5
        )
        ttk.Separator(slider_frame, orient='horizontal').grid(
            sticky='WE', columnspan=3, padx=5, pady=5
        )

        r += 2

        self.target_x_var = tk.DoubleVar()
        self.target_x_var.set(15)
        self.target_x_label = ttk.Label(slider_frame, text='Target X:')
        self.target_x_label.grid(row=r, padx=5)

        self.target_x_entry = ttk.Entry(
            slider_frame, textvariable=self.target_x_var, width=5
        )
        self.target_x_entry.grid(row=r, column=1, padx=5)
        self.target_x_entry.bind(
            '<Return>', lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.target_x_slider = ttk.Scale(
            slider_frame,
            variable=self.target_x_var,
            command=lambda x: self.update_targets(x=round(float(x), 2)),
            from_=0,
            to=30,
            orient='horizontal',
        )
        self.target_x_slider.grid(row=r, column=2, padx=5)

        r += 1

        self.target_y_var = tk.DoubleVar()
        self.target_y_label = ttk.Label(slider_frame, text='Target Y:')
        self.target_y_label.grid(row=r, padx=5)

        self.target_y_entry = ttk.Entry(
            slider_frame, textvariable=self.target_y_var, width=5
        )
        self.target_y_entry.grid(row=r, column=1, padx=5)
        self.target_y_entry.bind(
            '<Return>', lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.target_y_slider = ttk.Scale(
            slider_frame,
            variable=self.target_y_var,
            command=lambda y: self.update_targets(y=round(float(y), 2)),
            from_=-30,
            to=30,
            orient='horizontal',
        )
        self.target_y_slider.grid(row=r, column=2, padx=5)

        r += 1

        self.target_z_var = tk.DoubleVar()
        self.target_z_var.set(140/2)
        self.target_z_label = ttk.Label(slider_frame, text='Target Z:')
        self.target_z_label.grid(row=r, padx=5)

        self.target_z_entry = ttk.Entry(
            slider_frame, textvariable=self.target_z_var, width=5
        )
        self.target_z_entry.grid(row=r, column=1, padx=5)
        self.target_z_entry.bind(
            '<Return>', lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.target_z_slider = ttk.Scale(
            slider_frame,
            variable=self.target_z_var,
            command=lambda z: self.update_targets(z=round(float(z), 2)),
            from_=0,
            to=140,
            orient='horizontal',
        )
        self.target_z_slider.grid(row=r, column=2, padx=5)

        r += 1

        self.target_r_var = tk.DoubleVar()
        self.target_r_label = ttk.Label(slider_frame, text='Target R:')
        self.target_r_label.grid(row=r, padx=5)

        self.target_r_entry = ttk.Entry(
            slider_frame, textvariable=self.target_r_var, width=5
        )
        self.target_r_entry.grid(row=r, column=1, padx=5)
        self.target_r_entry.bind(
            '<Return>', lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.target_r_slider = ttk.Scale(
            slider_frame,
            variable=self.target_r_var,
            command=lambda r: self.update_targets(r=round(float(r), 2)),
            from_=-1.57,
            to=1.57,
            orient='horizontal',
        )
        self.target_r_slider.grid(row=r, column=2, padx=5)

        r += 1

        ttk.Label(slider_frame, text='End Effector', font='Helvetica 16 bold').grid(
            row=r, column=0, sticky='W', padx=5, pady=5
        )
        ttk.Separator(slider_frame, orient='horizontal').grid(
            sticky='WE', columnspan=3, padx=5, pady=5
        )

        r += 2

        self.target_e_var = tk.IntVar()
        self.target_e_var.set(sum(self.system.end_effector.value_range) // 2)
        self.target_e_label = ttk.Label(slider_frame, text='Target E:')
        self.target_e_label.grid(row=r, padx=5)

        self.target_e_entry = ttk.Entry(
            slider_frame, textvariable=self.target_e_var, width=5
        )
        self.target_e_entry.grid(row=r, column=1, padx=5)
        self.target_e_entry.bind(
            '<Return>', lambda _: Thread(target=self.jog, daemon=True).start()
        )

        self.target_e_slider = ttk.Scale(
            slider_frame,
            variable=self.target_e_var,
            command=lambda e: self.update_targets(e=round(float(e))),
            from_=self.system.end_effector.value_range[0],
            to=self.system.end_effector.value_range[1],
            orient='horizontal',
        )
        self.target_e_slider.grid(row=r, column=2, padx=5)

        r += 1

        self.hand_pos_var = tk.BooleanVar()
        self.hand_pos_toggle = ttk.Checkbutton(
            slider_frame,
            variable=self.hand_pos_var,
            text='Hand Position',
            command=lambda: Thread(
                target=self.hand_positioning, daemon=True).start(),
        )
        self.hand_pos_toggle.grid(row=r, column=0, sticky='W', padx=5, pady=5)

        self.realtime_var = tk.BooleanVar()
        self.realtime_toggle = ttk.Checkbutton(
            slider_frame, variable=self.realtime_var, text='Realtime'
        )
        self.realtime_toggle.grid(row=r, column=1, sticky='W', padx=5, pady=5)

        self.jog_button = ttk.Button(
            slider_frame, text='Jog', command=lambda: Thread(target=self.jog, daemon=True).start())
        self.jog_button.grid(row=r, column=2, padx=5, pady=5)

        r += 1

    def hand_positioning(self):
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

        self.realtime_var.set(True)

        while self.hand_pos_var.get():
            t1, t2, _, r = self.system.get_all_pos()
            x, y = self.system.polar_to_cartesian(t1, t2)
            self.target_x_var.set(round(x, 2))
            self.target_y_var.set(round(y, 2))
            self.target_r_var.set(round(r + t1, 2))

        self.realtime_var.set(False)
        self.motors_enabled(True)
        self.jog()

    def load_job(self):
        file_name = fd.askopenfilename(
            title='Select Job File',
            filetypes=[('GCode', '*.gcode')],
        )

        self.job_popup = tk.Toplevel(self)
        self.job_popup.geometry('500x100')
        self.job_popup.protocol('WM_DELETE_WINDOW', lambda: None)
        ttk.Label(self.job_popup, text='Running Job').pack(side='top')
        progress = 0
        progress_var = tk.IntVar()

        self.realtime_var.set(False)

        with open(file_name, 'r') as f:
            lines = f.readlines()
            progress_bar = ttk.Progressbar(
                self.job_popup, variable=progress_var, length=500, maximum=len(lines)
            )
            progress_bar.pack(fill='x', expand=1,
                              side='bottom', padx=10, pady=10)
            for line in lines:
                for argument, value in read_gcode_line(line):
                    if argument == 'X':
                        self.target_x_var.set(value)
                    elif argument == 'Y':
                        self.target_y_var.set(value)
                    elif argument == 'Z':
                        self.target_z_var.set(value)
                    elif argument == 'R':
                        self.target_r_var.set(value)
                    elif argument == 'E':
                        self.target_e_var.set(int(value))
                    elif argument == 'D':
                        self.move_duration_var.set(value)
                self.jog()
                progress += 1
                progress_var.set(progress)

        self.job_popup.destroy()

    def update_targets(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        r: Optional[float] = None,
        e: Optional[int] = None,
    ):
        digits = 3

        if x is not None:
            self.target_x_var.set(round(x, digits))
        if y is not None:
            self.target_y_var.set(round(y, digits))
        if z is not None:
            self.target_z_var.set(round(z, digits))
        if r is not None:
            self.target_r_var.set(round(r, digits))
        if e is not None:
            self.target_e_var.set(e)

        if self.realtime_var.get():
            self.jog()

    def jog(self):
        timeout = 5
        epsilon = 0.1

        self.jog_button['state'] = 'disabled'

        t1, t2 = self.system.cartesian_to_dual_polar(
            self.target_x_var.get(), self.target_y_var.get()
        )
        z = self.target_z_var.get()
        r = self.target_r_var.get()
        e = self.target_e_var.get()

        if self.realtime_var.get():
            self.system.jog(t1=t1, t2=t2, z=z, r=r, e=e)
        else:
            self.system.smooth_move(
                self.move_duration_var.get(),
                timeout=timeout,
                epsilon=epsilon,
                t1=t1,
                t2=t2,
                z=z,
                r=r,
                e=e,
            )

        self.jog_button['state'] = 'normal'

    def motors_enabled(self, value: bool):
        self.system.motors_enabled(value)
        self.motors_enabled_var.set(value)

    def on_close(self):
        self.motors_enabled(False)
        self.system.end_effector.move(10)
        self.root.destroy()
