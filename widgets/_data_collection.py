from threading import Thread
from re import L
from time import time

from random import randint
from math import cos, sin
from itertools import chain
from typing import Callable
import torch

from lib.app import Application
import tkinter as tk

from lib.mllib.common import *
from lib.utils import *
from lib.widget import Widget


class Trainer(Widget):
    def __init__(self, root, config):

        self.config = config
        super().__init__(root)

    def setup(self):
        self.title("Trainer")

        self.control._system.motorsEnabled(False)

        self.canvas = tk.Canvas(self, width=400, height=400, bg='white')
        self.canvas.pack()

        self.fpsVar = tk.IntVar()

        self.fpsLabel = tk.Label(self, textvariable=self.fpsVar)
        self.fpsLabel.pack()

        self.attrs: list[Callable] = [
            lambda: self.control._system.m2.position,
            lambda: self.control._system.m3.position,
            lambda: self.control._system.m2.velocity,
            lambda: self.control._system.m3.velocity,
        ]

        for motor in self.control._system.motors.values():
            motor.setControlMode('torque')
            motor.setPIDs('vel', .2, 20, 0, 0, F=0.01)
            motor.setPIDs('angle', 20, 0, 0, 0, F=0.01)
            motor.move(0)

        self.control._system.motorsEnabled(True)

        self.curr_l1 = self.canvas.create_line(0, 0, 0, 0, fill='black')
        self.curr_l2 = self.canvas.create_line(0, 0, 0, 0, fill='black')

        self.tar_l1 = self.canvas.create_line(
            0, 0, 0, 0, fill='blue', dash=(2, 2))
        self.tar_l2 = self.canvas.create_line(
            0, 0, 0, 0, fill='blue', dash=(2, 2))
        try:
            self.run()
        except Exception as e:
            for motor in self.control._system.motors.values():
                motor.disable()
            self.running = False
            raise e

    def run(self):
        for motor in self.control._system.motors.values():
            motor.move(0)

        params = {'batch_size': 64, 'gamma': 0.85, 'device': 'cuda', 'double': True,
                  'lr': 0.01, 'target_update': 3000, 'buffer_size': 10000, 'alpha': 0.6, 'beta': 0.4, 'replay_initial': 1000,
                  'epsilon_start': 1.0, 'epsilon_final': 0.01, 'epsilon_steps': 60000, 'torque_limit': 3.0, 'n_choices': 5, 'step_time': .1,
                  'new_target_time': 3.0, 'n_reps': 2}  # n_choices must be odd

        def get_torque(action):
            # First normalize action to [-1, 1]
            action = action / (params['n_choices'] - 1) * 2 - 1
            # Then scale to torque limit
            return round(action * params['torque_limit'], 2)

        buffer = PriorityBuffer(params['buffer_size'], params['alpha'])

        net = DQN(4, params['n_choices']**2).to(params['device'])
        tgt_net = DQN(4, params['n_choices']**2).to(params['device'])
        optimizer = torch.optim.Adam(net.parameters(), lr=params['lr'])
        step = 0

        current_state = None
        frame_start_time = time() - 1000
        new_position_start_time = time() - 1000

        self._target: list[float] = [0, 0]  # [m2p, m3p]
        self._out: list[float] = [0, 0]  # [m2t, m3t]
        new_target: bool = False

        self.running = True

        Thread(target=self._visualBase, daemon=True).start()
        Thread(target=self._visualWeights, daemon=True).start()

        while True:
            if time() - frame_start_time < params['step_time']:
                continue

            self.fpsVar.set(round(1 / (time() - frame_start_time), 2))
            frame_start_time = time()

            if time() - new_position_start_time > params['new_target_time']:
                t = randint(-157, 157)/100
                r = randint(10, 30)
                self.control.x = r*cos(t)
                self.control.y = r*sin(t)
                t1, t2 = self.control._system.cartesianToDualPolar(
                    self.control.x, self.control.y)
                self._target = [t1, t2]  # [m2p, m3p]
                self._out = [0, 0]  # [m2t, m3t]
                new_position_start_time = time()
                new_target = True

            last_state = current_state
            current_state = np.fromiter(
                (attr() for attr in self.attrs), dtype=np.float32)

            epsilon = max(params['epsilon_final'], params['epsilon_start'] - step * (
                params['epsilon_start'] - params['epsilon_final']) / params['epsilon_steps'])
            action_id = choose_action(
                net(torch.tensor(current_state, dtype=torch.float32).view(1, -1).to(params['device'])), epsilon)
            m2_action, m3_action = divmod(action_id, params['n_choices'])
            for i, (motor, val) in enumerate(zip([self.control._system.m2, self.control._system.m3],
                                                 (get_torque(m2_action), get_torque(m3_action)))):
                # no applying torque toward out of bounds
                threshold = 1.5 if i == 0 else 2.2
                if abs(val) > threshold and val * motor.position > 0:
                    val = -val / abs(val)  # sign
                val = clamp(val, -3, 3)
                val = round(val, 2)
                motor.move(val)
                self._out[i] = val

            if last_state is not None and not new_target:
                reward = -(sum(abs(t - r) for t, r in zip(self._target,
                           current_state))) * (1 - params['gamma'])
                experience = Experience(
                    last_state, action_id, reward, current_state, False)
                buffer.push(experience)
            new_target = False

            # Start training
            if len(buffer) < params['replay_initial']:
                continue
            for _ in range(params['n_reps']):
                batch, batch_indices, batch_weights = buffer.sample(
                    params['batch_size'], beta=params['beta'])

                batch_weights = torch.from_numpy(
                    batch_weights).to(params['device'])
                optimizer.zero_grad()
                losses = calc_losses(
                    batch, net, tgt_net, params['gamma'], params['device'], params['double'])
                buffer.update_priorities(
                    batch_indices, losses.detach().cpu().numpy())

                torch.sum(losses * batch_weights).backward()
                optimizer.step()

            step += 1
            if step % params['target_update'] == 0:
                # save model
                torch.save(net, 'model.pt')
                tgt_net.load_state_dict(net.state_dict())

    def drawArms(self, line1, line2, t1, t2):
        center = 200
        scale = 5
        x0 = center
        y0 = center
        x1 = x0 + scale*self.control._system.l1*cos(t1)
        y1 = y0 + scale*self.control._system.l1*sin(t1)
        x2 = x1 + scale*self.control._system.l2*cos(t1 + t2)
        y2 = y1 + scale*self.control._system.l2*sin(t1 + t2)
        self.canvas.coords(line1, x0, y0, x1, y1)
        self.canvas.coords(line2, x1, y1, x2, y2)

    def _visualBase(self):
        while self.running:
            self.drawArms(self.tar_l1, self.tar_l2,
                          self._target[0], self._target[1])
            self.drawArms(self.curr_l1, self.curr_l2, self.control._system.m2.position,
                          self.control._system.m3.position)

    def _visualWeights(self):
        self.canvas.itemconfig(
            self.curr_l1, width=2*abs(self._out[0])+0.1, fill=('green' if self._out[0] > 0 else 'red'))
        self.canvas.itemconfig(
            self.curr_l2, width=2*abs(self._out[1])+0.1, fill=('green' if self._out[1] > 0 else 'red'))


class TrainApp(Application):
    def __init__(self, root, train_config):
        super().__init__(root)
        self.train_config = train_config

    def createWidgets(self):
        super().createWidgets()
        self._data_collection = Trainer(self, self.train_config)
        self.toolsMenu.add_command(
            label='trainer', command=self._data_collection.show)
