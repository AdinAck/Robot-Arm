from threading import Thread
from abc import ABC, abstractmethod
import tkinter as tk

from lib.app import Application
from lib.system import System


class Control:
    _parent: Application
    _system: System

    def __init__(self, parent):
        self._parent = parent
        self._system = parent.system

    @property
    def x(self) -> float:
        return self._parent.targetXVar.get()

    @x.setter
    def x(self, value):
        self._parent.targetXVar.set(value)

    @property
    def y(self) -> float:
        return self._parent.targetYVar.get()

    @y.setter
    def y(self, value):
        return self._parent.targetYVar.set(value)

    @property
    def z(self) -> float:
        return self._parent.targetZVar.get()

    @z.setter
    def z(self, value):
        self._parent.targetZVar.set(value)

    @property
    def r(self) -> float:
        return self._parent.targetRVar.get()

    @r.setter
    def r(self, value):
        self._parent.targetRVar.set(value)

    @property
    def e(self) -> int:
        return self._parent.targetEVar.get()

    @e.setter
    def e(self, value):
        self._parent.targetEVar.set(value)

    def jog(self, *args, **kwargs):
        t1, t2 = self._system.cartesianToDualPolar(self.x, self.y)
        z = self.z
        r = self.r
        e = self.e

        if 'smooth' in args:
            assert 'duration' in kwargs, 'Duration must be specified for smooth move.'
            duration = kwargs['timeout']
            assert duration > 0, 'Timeout must be greater than 0.'

            assert 'timeout' in kwargs, 'Timeout must be specified for smooth move.'
            timeout = kwargs['timeout']
            assert timeout > 0, 'Timeout must be greater than 0.'

            assert 'epsilon' in kwargs, 'Epsilon must be specified for smooth move.'
            epsilon = kwargs['epsilon']
            assert epsilon > 0, 'Epsilon must be greater than 0.'

            self._system.smoothMove(
                duration, timeout, epsilon, t1=t1, t2=t2, z=z, r=r, e=e)
        else:
            self._system.jog(t1=t1, t2=t2, z=z, r=r, e=e)


class Widget(tk.Toplevel, ABC):
    control: Control
    alive: bool = False

    def __init__(self, parent):
        self.control = Control(parent)

    def show(self):
        if not self.alive:
            super().__init__(self.control._parent)
            self.resizable(False, False)
            self.protocol("WM_DELETE_WINDOW", self.close)

            self.alive = True

            Thread(target=self.setup, daemon=True).start()

    def close(self):
        self.destroy()
        self.alive = False

    @abstractmethod
    def setup(self):
        pass
