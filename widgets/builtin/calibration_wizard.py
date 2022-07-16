import os
import os.path
from threading import Thread
import tkinter.ttk as ttk
from tkinter import messagebox
from hardware.FOCMC_interface import MotorException

from lib.widget import Widget


class CalibrationWizard(Widget):
    content_frame: ttk.Frame
    continue_button: ttk.Button
    cancel_button: ttk.Button

    def setup(self):
        self.title('Calibration Wizard')
        self.geometry('400x400')

        self.control._system.motors_enabled(False)

        if not os.path.exists('config'):
            os.mkdir('config')

        self.step1()

    def step1(self):
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(side='top', fill='both', expand=True)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(10, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(2, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(side='bottom', fill='x')

        self.continue_button = ttk.Button(
            buttons, text='Continue', command=self.step2)
        self.continue_button.pack(side='right')
        self.cancel_button = ttk.Button(
            buttons, text='Cancel', command=self.close)
        self.cancel_button.pack(side='right')

        r, c = 1, 1

        ttk.Label(self.content_frame, text='Inner Rotational Motor', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5
        )
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )

        ttk.Label(
            self.content_frame,
            text="""The inner rotational motor requires manual calibration.
The motor will start slowly rotating left.
Let the motor spin as far as you are comfortable
and stop it with your hand when you are ready.
Click continue to begin.
                     """,
        ).grid(column=c, sticky='W', padx=5, pady=5)

    def step2(self):
        self.continue_button['text'] = 'Working...'
        self.continue_button['state'] = 'disabled'

        self.control._system.m_outer_rot.offset = 0
        self.control._system.m_inner_rot.offset = 0
        self.control._system.m_end_rot.offset = 0

        low = self.control._system.single_ended_home(
            self.control._system.m_inner_rot, voltage=-12, zeroSpeed=0.1, active=False
        )

        with open('config/inner_rot', 'w') as f:
            f.write(f'{low}\n')

        self.continue_button['command'] = self.step3
        self.continue_button['state'] = 'normal'
        self.continue_button['text'] = 'Continue'

        for child in self.content_frame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.content_frame, text='Inner Rotational Motor', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5
        )
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )

        ttk.Label(
            self.content_frame,
            text="""Now the motor will rotate to the right.
Let the motor spin as far as you are comfortable
and stop it with your hand when you are ready.
Click continue to begin.
                     """,
        ).grid(column=c, sticky='W', padx=5, pady=5)

    def step3(self):
        self.continue_button['text'] = 'Working...'
        self.continue_button['state'] = 'disabled'

        high = self.control._system.single_ended_home(
            self.control._system.m_inner_rot, voltage=12, zeroSpeed=0.1, active=False
        )

        with open('config/inner_rot', 'a') as f:
            f.write(f'{high}\n')

        self.continue_button['command'] = self.step4
        self.continue_button['state'] = 'normal'
        self.continue_button['text'] = 'Continue'

        for child in self.content_frame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.content_frame, text='Inner Rotational Motor', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5
        )
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )

        ttk.Label(
            self.content_frame,
            text="""Position the motor where you would like the center to be.
Click continue to begin.
                     """,
        ).grid(column=c, sticky='W', padx=5, pady=5)

    def step4(self):
        self.continue_button['text'] = 'Working...'
        self.continue_button['state'] = 'disabled'

        motor = self.control._system.m_inner_rot

        try:
            p = self.control._system.m_inner_rot.position
            motor.offset = center = p
        except MotorException:
            self.failed()
            return

        with open('config/inner_rot', 'a') as f:
            f.write(f'{center}\n')

        motor.set_control_mode('angle')
        motor.move(0)
        motor.enable()

        self.continue_button['command'] = self.step5
        self.continue_button['state'] = 'normal'
        self.continue_button['text'] = 'Continue'

        for child in self.content_frame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.content_frame, text='End Effector Rotational Motor', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5
        )
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )

        ttk.Label(
            self.content_frame,
            text="""Position the motor where you would like the left extreme to be.
Click continue to begin.""",
        ).grid(column=c, sticky='W', padx=5, pady=5)

    def step5(self, word='left'):
        self.continue_button['text'] = 'Working...'
        self.continue_button['state'] = 'disabled'

        motor = self.control._system.m_end_rot

        try:
            value = motor.position
        except MotorException:
            self.failed()
            return

        with open('config/end_rot', 'w' if word == 'left' else 'a') as f:
            f.write(f'{value}\n')

        if word != 'center':
            if word == 'left':
                self.continue_button['command'] = lambda: self.step5('right')
                word = 'right'
            elif word == 'right':
                self.continue_button['command'] = lambda: self.step5('center')
                word = 'center'
            word += ' extreme'

        self.continue_button['state'] = 'normal'
        self.continue_button['text'] = 'Continue'

        for child in self.content_frame.winfo_children():
            child.destroy()

        if word == 'center':
            self.control._system.m_end_rot.offset = value
            self.step6()
            return

        r, c = 1, 1

        ttk.Label(self.content_frame, text='End Effector Rotational Motor', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5
        )
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )
        ttk.Label(
            self.content_frame,
            text=f"""Position the motor where you would like the {word} to be.
Click continue to begin.""",
        ).grid(column=c, sticky='W', padx=5, pady=5)

    def step6(self):
        self.continue_button['text'] = 'Working...'
        self.continue_button['state'] = 'disabled'

        motor = self.control._system.m_end_rot

        motor.set_control_mode('angle')
        motor.move(0)
        motor.enable()

        self.continue_button['command'] = self.step7
        self.continue_button['state'] = 'normal'
        self.continue_button['text'] = 'Continue'

        for child in self.content_frame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(self.content_frame, text='Outer Rotational Motor', font='Helvetica 18 bold').grid(
            row=r, column=c, sticky='W', padx=5, pady=5
        )
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )
        ttk.Label(
            self.content_frame,
            text='The outer rotational motor can self calibrate,\nclick Continue to begin.',
        ).grid(column=c, sticky='W', padx=5, pady=5)

    def step7(self):
        self.continue_button['text'] = 'Working...'
        self.continue_button['state'] = 'disabled'

        with open('config/outer_rot', 'w') as f:
            for num in self.control._system.auto_calibrate(
                self.control._system.m_outer_rot, voltage=6, speed=2
            ):
                f.write(f'{num}\n')

        self.cancel_button.destroy()
        self.continue_button['command'] = self.close
        self.continue_button['state'] = 'normal'
        self.continue_button['text'] = 'Finish'

        for child in self.content_frame.winfo_children():
            child.destroy()

        r, c = 1, 1

        ttk.Label(
            self.content_frame, text='Calibration Complete', font='Helvetica 18 bold'
        ).grid(row=r, column=c, sticky='W', padx=5, pady=5)
        ttk.Separator(self.content_frame, orient='horizontal').grid(
            column=c, sticky='WE', padx=5, pady=5
        )

        ttk.Label(self.content_frame, text='Click finish to close this window.').grid(
            column=c, sticky='W', padx=5, pady=5
        )

        self.control._system.m_vertical.enable()

    def failed(self):
        msg = 'Calibration wizard failed.'
        messagebox.showwarning(__name__, msg)
        raise NotImplementedError()

    def close(self):
        self.control._system.motors_enabled(True)
        super().close()
