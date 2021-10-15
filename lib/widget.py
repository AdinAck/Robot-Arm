from abc import ABC, abstractmethod
import tkinter as tk
from typing import Optional

from lib.system import System


class Widget(tk.Toplevel, ABC):
    parent: tk.Tk
    system: System

    def __init__(self, parent):
        self.parent = parent

        self.system = self.parent.system

    def show(self):
        super().__init__(self.parent)
        self.resizable(False, False)

        self.setup()

    @abstractmethod
    def setup(self):
        pass
