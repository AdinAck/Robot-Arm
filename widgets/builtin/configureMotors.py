from threading import Thread
from time import sleep

import tkinter as tk
import tkinter.ttk as ttk

from lib.widget import Widget


class ConfigureMotors(Widget):
    selected_motor: int = 1

    def setup(self):
        self.title('Configure Motors')
        top_frame = ttk.Frame(self)
        top_frame.pack(side='top')

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side='bottom', fill='x')

        notebook = ttk.Notebook(self)
        notebook.pack(side='bottom', fill='both', expand=True)

        info_frame = ttk.Frame(notebook)
        info_frame.pack(fill='both', expand=True)
        info_frame.grid_rowconfigure(0, weight=1)
        info_frame.grid_rowconfigure(10, weight=1)
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)

        config_frame = ttk.Frame(notebook)
        config_frame.pack(fill='both', expand=True)
        config_frame.grid_rowconfigure(0, weight=1)
        config_frame.grid_rowconfigure(10, weight=1)
        config_frame.grid_columnconfigure(0, weight=1)
        config_frame.grid_columnconfigure(3, weight=1)

        pid_frame = ttk.Frame(notebook)
        pid_frame.pack(fill='both', expand=True)

        console_frame = ttk.Frame(notebook)
        console_frame.pack(fill='both', expand=True)

        notebook.add(info_frame, text='Info')
        notebook.add(config_frame, text='Config')
        notebook.add(pid_frame, text='PIDs')
        notebook.add(console_frame, text='Console')

        s = tk.StringVar()
        # motorSelect = ttk.OptionMenu(
        #     topFrame, s, f'Motor {list(self.system.motors.keys())[0]}', *[f'Motor {id}' for id in self.system.motors])
        motor_select = ttk.OptionMenu(
            top_frame, s, 'Motor 1', 'Motor 1', 'Motor 2', 'Motor 3', 'Motor 4', command=self._select_motor)
        motor_select.pack(side='left')
        ttk.Label(top_frame, text='❌').pack(side='left')

        ttk.Button(bottom_frame, text='Apply',
                   command=self.destroy).pack(side='right')

        ttk.Button(bottom_frame, text='Cancel',
                   command=self.destroy).pack(side='right')

        ttk.Button(bottom_frame, text='Ok',
                   command=self.destroy).pack(side='right')

        # Info
        r = 1
        c = 1

        ttk.Label(info_frame, text='USB',
                  font='Helvitica 12 bold').grid(row=r, column=c, sticky='W')
        ttk.Separator(info_frame, orient='horizontal').grid(
            column=c, sticky='WE', columnspan=2)

        r += 2

        ttk.Label(info_frame, text='Active:').grid(row=r, column=c, sticky='W')
        ttk.Label(info_frame, text='❌').grid(
            row=r, column=c+1, sticky='W')

        r += 1

        ttk.Label(info_frame, text='Port:').grid(row=r, column=c, sticky='W')
        ttk.Label(info_frame, text='？', foreground='orange').grid(
            row=r, column=c+1, sticky='W')

        r += 1

        ttk.Label(info_frame, text='Power',
                  font='Helvitica 12 bold').grid(row=r, column=c, sticky='W')
        ttk.Separator(info_frame, orient='horizontal').grid(
            column=c, sticky='WE', columnspan=2)

        r += 2

        ttk.Label(info_frame, text='External Supply:').grid(
            row=r, column=c, sticky='W')
        ttk.Label(info_frame, text='？', foreground='orange').grid(
            row=r, column=c+1, sticky='W')

        ttk.Label(info_frame, text='DRV8316',
                  font='Helvitica 12 bold').grid(column=c, sticky='W')
        ttk.Separator(info_frame, orient='horizontal').grid(
            column=c, sticky='WE', columnspan=2)

        r += 3

        ttk.Label(info_frame, text='Status:').grid(row=r, column=c, sticky='W')
        ttk.Label(info_frame, text='？', foreground='orange').grid(
            row=r, column=c+1, sticky='W')

        # Config
        r = 1
        c = 1

        self.motor_enabled_var = tk.BooleanVar()

        ttk.Checkbutton(config_frame, variable=self.motor_enabled_var,
                        text='Enabled').grid(row=r, column=c, sticky='W')

        r += 1

        self.voltage_limit_var = tk.DoubleVar()

        ttk.Label(config_frame, text='Voltage Limit:').grid(
            row=r, column=c, sticky='W')

        ttk.Entry(config_frame, textvariable=self.voltage_limit_var,
                  width=4).grid(row=r, column=c+1, sticky='W')

        r += 1

        self.velocity_limit_var = tk.DoubleVar()

        ttk.Label(config_frame, text='Velocity Limit:').grid(
            row=r, column=c, sticky='W')

        ttk.Entry(config_frame, textvariable=self.velocity_limit_var,
                  width=4).grid(row=r, column=c+1, sticky='W')

        r += 1

        self.control_mode_var = tk.DoubleVar()

        ttk.Label(config_frame, text='Control Mode:').grid(
            row=r, column=c, sticky='W')

        ttk.OptionMenu(config_frame, self.control_mode_var, 'torque', 'torque',
                       'velocity', 'angle').grid(row=r, column=c+1, sticky='W')

        # PIDs

        Thread(target=self._loop, daemon=True).start()

    def _select_motor(self, motor_id):
        self.selected_motor = motor_id

    def _loop(self):
        pass
