from threading import Thread
from abc import ABC, abstractmethod
import tkinter as tk

from lib.app import Application
from lib.system import System

from typing import Optional


class Control:
    """
    An abstraction for easily controlling and monitoring the system.

    Attributes
    ----------
    x: float (get/set)
        The x-coordinate of the system.
    y: float (get/set)
        The y-coordinate of the system.
    z: float (get/set)
        The z-coordinate of the system.
    r: float (get/set)
        The r-coordinate of the system (angle of end effector).
    e: float (get/set)
        The variable unit position of the end effector.
    """

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

    def jog(self, *args: str, duration: Optional[float] = None, timeout: float = None, epsilon: float = None):
        """
        Perform a movement to the target position.

        Parameters
        ----------
        *args: float
            Optional arguments to customize the movement.
                smooth: Literal['smooth']
                    Configure jog to be smooth.
        duration: Optional[float]
            The duration of the movement.
        timeout: Optional[float]
            The amount of time allotted to the move before a timeout exception is raised.
        epsilon: Optional[float]
            The amount of error allowed before the move is considered complete.
        """
        t1, t2 = self._system.cartesianToDualPolar(self.x, self.y)
        z = self.z
        r = self.r
        e = self.e

        if 'smooth' in args:
            assert duration is not None, 'Duration must be specified for smooth move.'
            assert duration > 0, 'Timeout must be greater than 0.'

            assert timeout is not None, 'Timeout must be specified for smooth move.'
            assert timeout > 0, 'Timeout must be greater than 0.'

            assert epsilon is not None, 'Epsilon must be specified for smooth move.'
            assert epsilon > 0, 'Epsilon must be greater than 0.'

            self._system.smoothMove(
                duration, timeout, epsilon, t1=t1, t2=t2, z=z, r=r, e=e
            )
        else:
            self._system.jog(t1=t1, t2=t2, z=z, r=r, e=e)


class Widget(tk.Toplevel, ABC):
    """
    Abstract class for creating a widget.

    A widget is an independent graphical window wich
    is able to control the system through the provided
    API-like structures.

    You must implement the setup() method.

    The setup() method is called when the widget is
    opened.

    Attributes
    ----------
    control: Control
        The control object for the system.
    alive: bool
        Whether or not the widget is alive.
    """
    control: Control
    alive: bool = False

    def __init__(self, parent):
        self.control = Control(parent)

    def show(self):
        if not self.alive:
            super().__init__(self.control._parent)
            self.resizable(False, False)
            self.protocol('WM_DELETE_WINDOW', self.close)

            self.alive = True

            Thread(target=self.setup, daemon=True).start()

    def close(self):
        self.destroy()
        self.alive = False

    @abstractmethod
    def setup(self):
        pass
