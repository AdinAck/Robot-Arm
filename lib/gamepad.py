from threading import Thread
from time import time
import hid

from lib.app import Application

# from lib.widget import Control


class GamePadDelegate:
    device: hid.Device
    app: Application

    def __init__(self, app: Application):
        self.app = app

        self.device = hid.Device(0x054c, 0x0268)
        Thread(target=self.event_loop, daemon=True).start()

    @staticmethod
    def map_range(range_in: tuple, range_out: tuple, val_in):
        return (val_in - range_in[0]) / (range_in[1] - range_in[0]) * (range_out[1] - range_out[0]) + range_out[0]
    
    @staticmethod
    def threshold(val, thresh, offset = 0):
        return val if (abs(val) > thresh) else offset
    
    @staticmethod
    def clamp(val, bounds: tuple):
        return min(max(val, bounds[0]), bounds[1])

    @staticmethod
    def _signed_ceil(val):
        c = int(val) != val
        return int(val) + c if val > 0 else int(val) - c

    def event_loop(self):
        start = time()

        while True:
            report = self.device.read(64)
            _vals = list(report)

            delta = 10 * (time() - start)

            r = self.clamp(
                self.app.target_r_var.get() + delta * self.threshold(
                    self.map_range(
                        (0, 255),
                        (-0.5, 0.5),
                        _vals[6]
                    ),
                    0.1
                ),
                (-1.57, 1.57)
                )
            z = self.clamp(
                self.app.target_z_var.get() + delta * self.threshold(
                    self.map_range(
                        (0, 255),
                        (-10, 10),
                        _vals[7]
                    ),
                    1
                ),
                (0, 160)
            )
            x = self.clamp(
                self.app.target_x_var.get() + delta * self.threshold(
                    self.map_range(
                        (0, 255),
                        (-5, 5),
                        _vals[8]
                    ),
                    0.5
                ),
                (0, 30)
            )
            y = self.clamp(
                self.app.target_y_var.get() + delta * self.threshold(
                    self.map_range(
                        (0, 255),
                        (-5, 5),
                        _vals[9]
                    ),
                    0.5
                ),
                (-30, 30)
            )

            e = self.clamp(
                self.app.target_e_var.get() + self._signed_ceil(delta * self.threshold(
                    self.map_range(
                        (-255, 255),
                        (-10, 10),
                        _vals[19] - _vals[18]
                    ),
                    1
                )),
                (0, 100)
            )

            self.app.update_targets(
                x,
                y,
                z,
                r,
                e
            )

            start = time()



