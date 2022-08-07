import itertools
from time import sleep, time
import tkinter as tk
import tkinter.ttk as ttk

import copy
from random import random
import numpy as np
from typing import Tuple
import torch
import torch.nn as nn
import torch.functional as F
import torch.optim as optim
from lib.mllib.model import Actor, QNetwork, VNetwork
from lib.mllib.replay_memory import Replay

from hardware.FOCMC_interface import Motor
from lib.system import System
from lib.widget import Widget


class Env:
    system: System

    m1: Motor
    m2: Motor
    m3: Motor

    target: Tuple[float, float]

    state: tuple
    x: float
    y: float
    reward: float
    is_done: int
    distance: float

    _start: float

    def __init__(self, system: System):
        self.system = system

        self.m1 = system.m_inner_rot
        self.m2 = system.m_outer_rot
        self.m3 = system.m_end_rot

        self._start = time()

    def __enter__(self):
        self.m1.set_control_mode("torque")
        self.m2.set_control_mode("torque")

        return self

    def __exit__(self):
        self.m1.set_control_mode("angle")
        self.m2.set_control_mode("angle")
        self.m1.move(0)
        self.m2.move(0)

    def fetch(self) -> tuple:
        p1 = self.m1.position
        v1 = self.m1.velocity
        p2 = self.m2.position
        v2 = self.m2.velocity
        p3 = self.m3.position
        v3 = self.m3.velocity

        self.x, self.y = self.system.polar_to_cartesian(p1, p2)
        target_p1, target_p2 = self.system.cartesian_to_dual_polar(self.x, self.y)

        return p1, v1, p2, v2, p3, v3, target_p1, target_p2

    def step(self, t1: float, t2: float, timeout=5) -> tuple:
        self.m1.move(t1)
        self.m2.move(t2)

        self.state = self.fetch()
        self.reward = self.get_reward()

        if time() - self._start > timeout:
            self.is_done = -1
            self._start = time()
        else:
            self.is_done = self.get_is_done()

        return self.state, self.reward, self.is_done

    def get_reward(self) -> float:
        # inverse of distance between current and target position
        self.distance = self._distance(
            (self.x, self.target[0]),
            (self.y, self.target[1]),
            (0, self.state[1]),
            (0, self.state[3]),
        )
        return 1 / self.distance

    def get_is_done(self, epsilon=0.1) -> int:
        return 1 if self.distance < epsilon else 0

    def reset(self):
        t1 = random() * 4 - 2
        t2 = random() * 4 - 2

        self.target = self.system.polar_to_cartesian(t1, t2)

        sleep(1)

        return self.fetch()

    @staticmethod
    def _distance(*pairs: tuple) -> float:
        return sum((p1 - p2) ** 2 for p1, p2 in pairs) ** 0.5


class SAC:
    def __init__(self, state_size, args):
        self.gamma = args["gamma"]
        self.alpha = args["alpha"]
        self.update_interval = args["update_interval"]
        self.max_torque = args["max_torque"]

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.critic = QNetwork(state_size).to(self.device)
        self.critic_optim = optim.Adam(self.critic.parameters(), lr=3e-4)
        self.critic_target = copy.deepcopy(self.critic)

        self.actor = Actor(state_size, self.max_torque).to(self.device)
        self.actor_optim = optim.Adam(self.actor.parameters(), lr=3e-4)

    def select_action(self, state, eval=False):
        state = torch.Tensor(state).to(self.device).unsqueeze(0)
        if eval:
            _, _, action = self.actor.sample(state)
        else:
            action, _, _ = self.actor.sample(state)
        return action.cpu().detach().numpy()

    def update_model(self, memory: Replay, batch_size, updates):
        states, actions, rewards, next_states, dones = memory.sample(batch_size)

        states = torch.Tensor(states).to(self.device)
        actions = torch.Tensor(actions).to(self.device)
        rewards = torch.Tensor(rewards).to(self.device).unsqueeze(1)
        next_states = torch.Tensor(next_states).to(self.device)
        dones = torch.Tensor(dones).to(self.device).unsqueeze(1)

        with torch.no_grad:
            next_action, next_log_pi, _ = self.actor.sample(next_states)
            next_qf1, next_qf2 = self.critic_target(next_states, next_action)
            next_qf = min(next_qf1, next_qf2) - self.alpha * next_log_pi
            next_q = rewards + dones * self.gamma * next_qf
        qf1, qf2 = self.critic(states, actions)
        qf1_loss = F.mse_loss(qf1, next_q)
        qf2_loss = F.mse_loss(qf2, next_q)
        qf_loss = qf1_loss + qf2_loss

        self.critic_optim.zero_grad()
        qf_loss.backward()
        self.critic_optim.step()

        pi, log_pi, _ = self.actor.sample(states)
        qf_pi = self.critic(states, pi)
        actor_loss = (
            (self.alpha * log_pi) - qf_pi
        ).mean()  # Jπ = 𝔼st∼D,εt∼N[α * logπ(f(εt;st)|st) − Q(st,f(εt;st))]

        self.actor_optim.zero_grad()
        actor_loss.backward()
        self.actor_optim.step()

        if updates % self.update_interval == 0:
            self.critic_target.load_state_dict(self.critic.state_dict())

        return qf1_loss, qf2_loss, actor_loss


class Train(Widget):
    def setup(self):
        ttk.Label(self, text="Train").pack(padx=10, pady=10)
        args = {
            "alpha": 0.2,
            "gamma": 0.99,
            "update_interval": 1,
            "max_torque": 12,
            "batch_size": 64,
        }

        state_size = 8
        agent = SAC(state_size, args)
        memory = Replay(25000)
        start_steps = 10000
        total_steps = 0
        updates = 0
        with Env(self.control._system) as env:
            for i in itertools.count(1):
                episode_reward = 0
                episode_steps = 0
                done = False
                state = env.reset()
                while not done:
                    action = (
                        np.random((1, 2)) * args["max_torque"] * 2 - args["max_torque"]
                        if start_steps > total_steps
                        else agent.select_action(state)
                    )

                    if len(memory) > args["batch_size"]:
                        c1_loss, c2_loss, a_loss = agent.update_model(
                            memory, args["batch_size"], updates
                        )

                        # TENSORBOARD LOGGING
                        updates += 1

                    next_state, reward, done = env.step(action[0], action[1])
                    episode_steps += 1
                    total_steps += 1
                    episode_reward += reward
                    mask = 0 if done == -1 else done

                    memory.push(state, action, reward, next_state, mask)

                    state = next_state
                print(
                    f"Episode {i}, episode steps {episode_steps}, episode reward {episode_reward}"
                )
