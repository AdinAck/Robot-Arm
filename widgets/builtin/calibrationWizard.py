import tkinter.ttk as ttk

from lib.widget import Widget


class CalibrationWizard(Widget):
    contentFrame: ttk.Frame
    continueButton: ttk.Button
    cancelButton: ttk.Button

    def setup(self):
        self.title('Calibration Wizard')
        self.geometry('400x400')

        self.control._system.motorsEnabled(False)
        self.step1()

    def step1(self):
        self.contentFrame = ttk.Frame(self)
        self.contentFrame.pack(side='top', fill='both', expand=True)
        self.contentFrame.grid_rowconfigure(0, weight=1)
        self.contentFrame.grid_rowconfigure(10, weight=1)
        self.contentFrame.grid_columnconfigure(0, weight=1)
        self.contentFrame.grid_columnconfigure(2, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(side='bottom', fill='x')

        self.continueButton = ttk.Button(
            buttons, text='Continue', command=self.step2)
        self.continueButton.pack(side='right')
        self.cancelButton = ttk.Button(buttons, text='Cancel',
                                       command=self.close)
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

    def step2(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        self.control._system.m3.offset = 0
        self.control._system.m2.offset = 0
        self.control._system.m4.offset = 0

        low = self.control._system.singleEndedHome(
            self.control._system.m2,
            voltage=-12,
            zeroSpeed=0.1,
            active=False
        )

        with open('config/m2', 'w') as f:
            f.write(f'{low}\n')

        self.continueButton['command'] = self.step3
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

    def step3(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        high = self.control._system.singleEndedHome(
            self.control._system.m2,
            voltage=12,
            zeroSpeed=0.1,
            active=False
        )

        with open('config/m2', 'a') as f:
            f.write(f'{high}\n')

        self.continueButton['command'] = self.step4
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

    def step4(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.control._system.m2

        if (p := self.control._system.m2.position) is not None:
            motor.offset = center = p
        else:
            self.failed()
            return

        with open('config/m2', 'a') as f:
            f.write(f'{center}\n')

        motor.setControlMode('angle')
        motor.move(0)
        motor.enable()

        self.continueButton['command'] = self.step5
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

    def step5(self, word='left'):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.control._system.m4

        if (p := motor.position) is not None:
            value = p
        else:
            self.failed()
            return

        with open('config/m4', 'w' if word == 'left' else 'a') as f:
            f.write(f'{value}\n')

        if word != 'center':
            if word == 'left':
                self.continueButton['command'] = lambda: self.step5(
                    'right')
                word = 'right'
            elif word == 'right':
                self.continueButton['command'] = lambda: self.step5(
                    'center')
                word = 'center'
            word += ' extreme'

        self.continueButton['state'] = 'normal'
        self.continueButton['text'] = 'Continue'

        for child in self.contentFrame.winfo_children():
            child.destroy()

        if word == 'center':
            self.control._system.m4.offset = value
            self.step6()
            return

        r, c = 1, 1

        ttk.Label(self.contentFrame, text='Motor 4', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.contentFrame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5)
        ttk.Label(self.contentFrame, text=f"""Position the motor where you would like the {word} to be.
Click continue to begin."""
                  ).grid(column=c, sticky='W', padx=5, pady=5)

    def step6(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        motor = self.control._system.m4

        motor.setControlMode('angle')
        motor.move(0)
        motor.enable()

        self.continueButton['command'] = self.step7
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

    def step7(self):
        self.continueButton['text'] = 'Working...'
        self.continueButton['state'] = 'disabled'

        with open('config/m3', 'w') as f:
            for num in self.control._system.autoCalibrate(self.control._system.m3, speed=2):
                f.write(f'{num}\n')

        self.cancelButton.destroy()
        self.continueButton['command'] = self.close
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

        self.control._system.m1.enable()

    def failed(self):
        raise NotImplementedError('Calibration wizard failed.')

    def close(self):
        self.control._system.motorsEnabled(True)
        super().close()
