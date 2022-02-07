from threading import Thread
from math import cos, sin

import tkinter as tk

from lib.widget import Widget


class Visual(Widget):
    running = True

    def setup(self):
        self.canvas = tk.Canvas(self, width=400, height=400, bg="white")
        self.canvas.pack()

        self.curr_l1 = self.canvas.create_line(0, 0, 0, 0, fill="black")
        self.curr_l2 = self.canvas.create_line(0, 0, 0, 0, fill="black")

        self.tar_l1 = self.canvas.create_line(0, 0, 0, 0, fill="blue", dash=(2, 2))
        self.tar_l2 = self.canvas.create_line(0, 0, 0, 0, fill="blue", dash=(2, 2))

        Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while self.running:
            t1, t2 = self.control._system.cartesianToDualPolar(
                self.control.x, self.control.y
            )
            self._drawArms(self.tar_l1, self.tar_l2, t1, t2)

            self._drawArms(
                self.curr_l1,
                self.curr_l2,
                self.control._system.m_inner_rot.position,
                self.control._system.m_outer_rot.position,
                (
                    self.control._system.m_inner_rot._sendCommand("MMG1", float),
                    self.control._system.m_outer_rot._sendCommand("MMG1", float),
                ),
            )

    def _drawArms(self, line1, line2, t1, t2, torques=None):
        center = 200
        scale = 5
        x0 = center
        y0 = center
        x1 = x0 + scale * self.control._system.l1 * cos(t1)
        y1 = y0 + scale * self.control._system.l1 * sin(t1)
        x2 = x1 + scale * self.control._system.l2 * cos(t1 + t2)
        y2 = y1 + scale * self.control._system.l2 * sin(t1 + t2)
        self.canvas.coords(line1, x0, y0, x1, y1)
        self.canvas.coords(line2, x1, y1, x2, y2)

        if torques is not None:
            self.canvas.itemconfig(
                line1,
                width=2 * abs(torques[0]) + 0.1,
                fill=("green" if torques[0] > 0 else "red"),
            )
            self.canvas.itemconfig(
                line2,
                width=2 * abs(torques[1]) + 0.1,
                fill=("green" if torques[1] > 0 else "red"),
            )

    def close(self):
        self.running = False
        super().close()
