from threading import Thread
from abc import ABC, abstractmethod
import tkinter as tk

from lib.app import Application
from lib.system import System

from typing import Optional, Union, TypeVar

T = TypeVar('T', float, int)

def _clamp(value: Optional[T], m: Union[float, int], M: Union[float, int]) -> Optional[T]:
    if value is not None:
        return type(value)(min(max(value, m), M))

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

    def __init__(self, parent):
        self._parent: Application = parent
        self._system: System = parent.system

    @property
    def target_x(self):
        return self._parent.target_x_var.get()

    @property
    def target_y(self):
        return self._parent.target_y_var.get()

    @property
    def target_z(self):
        return self._parent.target_z_var.get()

    @property
    def target_r(self):
        return self._parent.target_r_var.get()

    @property
    def target_e(self):
        return self._parent.target_e_var.get()

    @property
    def position(self) -> tuple[float, float, float, float]:
        """
        Property for the current position of the system.

        Returns
        -------
        tuple[float, float, float, float, int]
            x, y, z, r, e positions.
        """

        t1, t2, z = self._system.get_all_pos()

        return self._system.polar_to_cartesian(t1, t2) + (z, self._system.m_end_rot.position)

    def move(self, *args: str,
             x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None, r: Optional[float] = None, e: Optional[int] = None,
             duration: float = 2, timeout: float = 5, epsilon: float = 0.1):
        """
        Perform a movement to the target position.

        Parameters
        ----------
        *args: float
            Optional arguments to customize the movement.
                smooth: Literal['smooth']
                    Configure jog to be smooth.
        x: Optional[float]
            The x-coordinate to move to.
        y: Optional[float]
            The y-coordinate to move to.
        z: Optional[float]
            The z-coordinate to move to.
        r: Optional[float]
            The end effector rotation to move to.
        e: Optional[int]
            The end effector position to move to.
        duration: Optional[float]
            The duration of the movement.
        timeout: Optional[float]
            The amount of time allotted to the move before a timeout exception is raised.
        epsilon: Optional[float]
            The amount of error allowed before the move is considered complete.
        """

        self._parent.update_targets(
            x=_clamp(x, 0, 30),
            y=_clamp(y, -30, 30),
            z=_clamp(z, 0, 160),
            r=_clamp(r, -1.57, 1.57),
            e=_clamp(e, 0, 100)
        )

        t1, t2 = self._system.cartesian_to_dual_polar(
            self._parent.target_x_var.get(), self._parent.target_y_var.get()
        )
        z = self._parent.target_z_var.get()
        r = self._parent.target_r_var.get()
        e = self._parent.target_e_var.get()

        if 'smooth' in args:
            assert duration > 0, 'Duration must be greater than 0.'
            assert timeout > 0, 'Timeout must be greater than 0.'
            assert epsilon > 0, 'Epsilon must be greater than 0.'

            self._system.smooth_move(
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
