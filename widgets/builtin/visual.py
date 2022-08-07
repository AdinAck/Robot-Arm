from threading import Thread
from math import cos, pi, sin

import tkinter as tk

from lib.widget import Widget


class Visual(Widget):
    running: bool

    def setup(self):
        self.running = True
        self.canvas = tk.Canvas(self, width=400, height=400, bg='white')
        self.canvas.pack()

        self.curr_l1 = self.canvas.create_line(0, 0, 0, 0, fill='black')
        self.curr_l2 = self.canvas.create_line(0, 0, 0, 0, fill='black')
        self.curr_r = self.canvas.create_line(0, 0, 0, 0, fill='black')

        self.tar_l1 = self.canvas.create_line(
            0, 0, 0, 0, fill='blue', dash=(2, 2))
        self.tar_l2 = self.canvas.create_line(
            0, 0, 0, 0, fill='blue', dash=(2, 2))
        self.tar_r = self.canvas.create_line(0, 0, 0, 0, fill='blue', dash=(2, 2))

        Thread(target=self.loop, daemon=True).start()

    def loop(self):
        try:
            while self.running:
                t1, t2 = self.control._system.cartesian_to_dual_polar(
                    self.control.target_x, self.control.target_y
                )
                r = self.control.target_r

                self._drawArms(self.tar_l1, self.tar_l2, self.tar_r, t1, t2, r)

                c_t1, c_t2, c_r = (
                    self.control._system.m_inner_rot.position,
                    self.control._system.m_outer_rot.position,
                    self.control._system.m_end_rot.position
                )

                self._drawArms(
                    self.curr_l1,
                    self.curr_l2,
                    self.curr_r,
                    c_t1,
                    c_t2,
                    c_r + c_t1,
                    (
                        self.control._system.m_inner_rot._send_command(
                            'MMG1', float),
                        self.control._system.m_outer_rot._send_command(
                            'MMG1', float),
                        self.control._system.m_end_rot._send_command(
                            'MMG1', float
                        )
                    )
                )
        except tk.TclError:
            self.close()

    def _drawArms(self, line1, line2, line3, t1, t2, r, torques=None):
        center = 200
        scale = 5
        x0 = center
        y0 = center
        x1 = x0 + scale * self.control._system.l1 * cos(t1)
        y1 = y0 + scale * self.control._system.l1 * sin(t1)
        x2 = x1 + scale * self.control._system.l2 * cos(t1 + t2)
        y2 = y1 + scale * self.control._system.l2 * sin(t1 + t2)

        end_effector_size = self.control.target_e / 100 * 5

        x3 = x2 - scale * end_effector_size * cos(r + pi/2)
        y3 = y2 - scale * end_effector_size * sin(r + pi/2)
        x4 = x2 + scale * end_effector_size * cos(r + pi/2)
        y4 = y2 + scale * end_effector_size * sin(r + pi/2)

        self.canvas.coords(line1, x0, y0, x1, y1)
        self.canvas.coords(line2, x1, y1, x2, y2)
        self.canvas.coords(line3, x3, y3, x4, y4)

        if torques is not None:
            self.canvas.itemconfig(
                line1,
                width=2 * abs(torques[0]) + 0.1,
                fill=('green' if torques[0] > 0 else 'red'),
            )
            self.canvas.itemconfig(
                line2,
                width=2 * abs(torques[1]) + 0.1,
                fill=('green' if torques[1] > 0 else 'red'),
            )
            self.canvas.itemconfig(
                line3,
                width=2 * abs(torques[2]) + 0.1,
                fill=('green' if torques[2] > 0 else 'red'),
            )

    def close(self):
        self.running = False
        super().close()
