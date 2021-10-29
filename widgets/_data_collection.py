from re import L
from time import time, sleep
import pickle
from random import randint
from math import cos, sin, sqrt
from itertools import chain
from typing import Callable
import torch
import logging

from lib.app import Application
import tkinter as tk

import neat
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

        self.curr_l1 = self.canvas.create_line(0,0,0,0, fill='black')
        self.curr_l2 = self.canvas.create_line(0,0,0,0, fill='black')

        self.tar_l1 = self.canvas.create_line(0,0,0,0, fill='blue', dash=(2, 2))
        self.tar_l2 = self.canvas.create_line(0,0,0,0, fill='blue', dash=(2, 2))

        self.run()
    
    
    def run(self):
        self.model = DQN(self.runModel, self.config.neat_config, self.config.checkpoint)
        self.model.train(self.config.generations)
        for motor in self.control._system.motors.values():
            motor.disable()

    def drawArms(self, line1, line2, t1, t2, torques=None):
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

        if torques is not None:
            self.canvas.itemconfig(line1, width=2*abs(torques[0])+0.1, fill=('green' if torques[0] > 0 else 'red'))
            self.canvas.itemconfig(line2, width=2*abs(torques[1])+0.1, fill=('green' if torques[1] > 0 else 'red'))


    def runModel(self):
        # logging.getLogger().setLevel(logging.DEBUG)
        for motor in self.control._system.motors.values():
            motor.move(0)
        
        params = {'batch_size': 64, 'gamma': 0.9, 'device': 'cpu', 'double': True, 
        'lr': 0.01, 'target_update': 1000, 'buffer_size': 10000, 'alpha': 0.6, 'beta': 0.4, 'replay_initial': 1000,
        'epsilon_start': 1.0, 'epsilon_final': 0.01, 'epsilon_steps': 1000, 'torque_limit': 3.0, 'n_choices': 21, 'step_time': .1} # n_choices must be odd
        buffer = PriorityBuffer(params['buffer_size'], params['alpha'])
        
        net = DQN(4, params['n_choices']**2)
        tgt_net = net
        optimizer = torch.optim.Adam(net.parameters(), lr=params['lr'])
        step = 0
        
        t = randint(-157, 157)/100
        r = randint(10, 30)
        self.control.x = r*cos(t)
        self.control.y = r*sin(t)
        t1, t2 = self.control._system.cartesianToDualPolar(
            self.control.x, self.control.y)
        target: list[float] = [t1, t2]  # [m2p, m3p]
        out: list[float] = [0, 0]  # [m2t, m3t]
        current_state = None
        start_time = -100
        while True:
            if time() - start_time < params['step_time']:
                continue
            start_time = time()
            last_state = current_state
            current_state = np.fromiter(attr() for attr in self.attrs)

            epsilon = max(params['epsilon_final'], params['epsilon_start'] - step * (params['epsilon_start'] - params['epsilon_final']) / params['epsilon_steps'])
            action_id = choose_action(net(torch.tensor(current_state, dtype=torch.float32).view(1, -1)), epsilon)
            m2_action, m3_action = divmod(action_id, params['n_choices'])
            def get_torque(action):
                # First normalize action to [-1, 1]
                action = (action / (params['n_choices'] - 1) / 2) - 1
                # Then scale to torque limit
                return action * params['torque_limit']
            self.control._system.m2.move(get_torque(m2_action))
            self.control._system.m3.move(get_torque(m3_action))

                
            self.drawArms(self.tar_l1, self.tar_l2, target[0], target[1])
            self.drawArms(self.curr_l1, self.curr_l2, self.control._system.m2.position,
                        self.control._system.m3.position, out)

            step += 1

            if last_state is not None:
                reward = -(sum(abs(t - r) for t, r in zip(target, current_state)))
                experience = Experience(last_state, action_id, reward, current_state, False)
                buffer.push(experience)

            # Start training
            if len(buffer) < params['replay_initial']:
                continue

            batch, batch_indices, batch_weights = buffer.sample(params['batch_size'], beta=params['beta'])
            batch_weights = torch.Tensor(batch_weights, device=params['device'])
            optimizer.zero_grad()
            losses = calc_losses(batch, net, tgt_net, params['gamma'], params['device'], params['double'])
            buffer.update_priorities(batch_indices, losses.detach().cpu().numpy())

            torch.sum(losses * batch_weights).backward()
            optimizer.step()
            step += 1
            if step % params['target_update'] == 0:
                tgt_net = net

class TrainApp(Application):
    def __init__(self, root, train_config):
        super().__init__(root)
        self.train_config = train_config
    
    def createWidgets(self):
        super().createWidgets()
        self._data_collection = Trainer(self, self.train_config)
        self.toolsMenu.add_command(
            label='trainer', command=self._data_collection.show)
