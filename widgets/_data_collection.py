from time import sleep

import tkinter as tk
from typing import Callable

from lib.widget import Widget


def _compare(a, b):
    assert len(a) == len(b)
    return sum(abs(i - j) for i, j in zip(a, b))


class Model:
    def predict(self) -> list:
        return []


class Trainer(Widget):
    model: Model
    stepSize = 0.1

    def setup(self):
        self.title("Trainer")

        self.control._system.motorsEnabled(False)

        self.startButton = tk.Button(self, text='Start', command=self.runModel)
        self.startButton.pack()

    def runModel(self):
        self.startButton['state'] = 'dsiabled'

        for motor in self.control._system.motors.values():
            motor.setControlMode('torque')
            motor.move(0)

        attrs: list[Callable] = [
            lambda: self.control._system.m2.position,
            lambda: self.control._system.m2.velocity,
            lambda: self.control._system.m3.position,
            lambda: self.control._system.m3.velocity,
        ]

        t1, t2 = self.control._system.cartesianToDualPolar(
            self.control.x, self.control.y)

        target: list[float] = [t1, 0, t2, 0]  # [m2p, m2v, m3p, m3v]

        assert len(target) == len(attrs)
        throughput = len(target)

        out: list[float] = [0, 0]  # [m2t, m3t]

        with open('log', 'w') as f:
            while (error := _compare(out, (current := (attr() for attr in attrs)))) > 0.1 * throughput:
                out = self.model.predict(*target, *current)
                for motor, val in zip(self.control._system.motors.values(), out):
                    motor.move(val)

                f.write(
                    f'{", ".join((str(f) for f in current))}, {", ".join((str(f) for f in out))}, {error}\n')
                sleep(self.stepSize)
