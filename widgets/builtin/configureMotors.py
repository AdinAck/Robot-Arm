import tkinter as tk
import tkinter.ttk as ttk

from lib.widget import Widget


class ConfigureMotors(Widget):
    def setup(self):
        self.title('Configure Motors')
        topFrame = ttk.Frame(self)
        topFrame.pack(side='top')

        bottomFrame = ttk.Frame(self)
        bottomFrame.pack(side='bottom', fill='x')

        notebook = ttk.Notebook(self)
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
        #     topFrame, s, f'Motor {list(self.system.motors.keys())[0]}', *[f'Motor {id}' for id in self.system.motors])
        motorSelect = ttk.OptionMenu(
            topFrame, s, 'Motor 1', 'Motor 1', 'Motor 2', 'Motor 3', 'Motor 4', command=self.selectMotor)
        motorSelect.pack(side='left')
        ttk.Label(topFrame, text='❌').pack(side='left')

        ttk.Button(bottomFrame, text='Apply',
                   command=self.destroy).pack(side='right')

        ttk.Button(bottomFrame, text='Cancel',
                   command=self.destroy).pack(side='right')

        ttk.Button(bottomFrame, text='Ok',
                   command=self.destroy).pack(side='right')

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

    def selectMotor(self, motor):
        raise NotImplementedError(
            "This should somehow select what motor is being configured by the motor configuration panel.")
