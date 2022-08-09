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
import torch.optim as optim
from lib.mllib.model import Actor, QNetwork, VNetwork
from lib.mllib.replay_memory import Replay
from torch.utils.tensorboard import SummaryWriter
from time import time

from hardware.FOCMC_interface import Motor
from lib.system import System
from lib.utils import threaded_callback
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

    def __exit__(self, exc_type, exc_value, exc_traceback):
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
        target_p1, target_p2 = self.system.cartesian_to_dual_polar(*self.target)

        return p1, v1, p2, v2, p3, v3, target_p1, target_p2

    def step(self, t1: float, t2: float, timeout=5) -> tuple:
        start_state = self.state

        self.m1.move(round(t1, 3))
        self.m2.move(round(t2, 3))

        sleep(0.1)

        self.state = self.fetch()
        self.distance = self._distance(
            (self.state[0], self.state[6]),
            (self.state[2], self.state[7]),
            (0, self.state[1]),
            (0, self.state[3]),
        )
        self.reward = self.get_reward(start_state)

        if time() - self._start > timeout:
            self.is_done = -1
            self._start = time()
        else:
            self.is_done = self.get_is_done()

        return self.state, self.reward, self.is_done

    def get_reward(self, old: tuple) -> float:
        # sum of change in error for each motor

        d1 = abs(old[0] - self.target[0]) - abs(self.state[0] - self.target[0])
        d2 = abs(old[2] - self.target[1]) - abs(self.state[2] - self.target[1])

        return d1 + d2

    def get_is_done(self, epsilon=0.1) -> int:
        return 1 if self.distance < epsilon else 0

    def reset(self):
        self.m1.move(0)
        self.m2.move(0)

        t1 = random() * 2 - 1
        t2 = random() * 4 - 2

        self.target = self.system.polar_to_cartesian(t1, t2)

        sleep(1)

        self.state = self.fetch()

        return self.state

    @staticmethod
    def _distance(*pairs: tuple) -> float:
        return sum((p1 - p2) ** 2 for p1, p2 in pairs) ** 0.5


class SAC:
    def __init__(self, state_size, args):
        self.gamma = args["gamma"]
        self.alpha = args["alpha"]
        self.update_interval = args["update_interval"]
        self.max_torque = args["max_torque"]
        self.entropy_tune = args["entropy_tune"]

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.critic = QNetwork(state_size).to(self.device)
        self.critic_optim = optim.Adam(self.critic.parameters(), lr=3e-4)
        self.critic_target = copy.deepcopy(self.critic)

        self.actor = Actor(state_size, self.max_torque).to(self.device)
        self.actor_optim = optim.Adam(self.actor.parameters(), lr=3e-4)

        if self.entropy_tune:
            self.target_entropy = -2
            self.log_alpha = torch.zeros(1, requires_grad=True, device=self.device)
            self.alpha_optim = optim.Adam([self.log_alpha], 3e-4)

    def select_action(self, state, eval=False):
        state = torch.Tensor(state).to(self.device).unsqueeze(0)
        if eval:
            _, _, action = self.actor.sample(state)
        else:
            action, _, _ = self.actor.sample(state)
        return action.cpu().squeeze().detach().numpy()

    def update_model(self, memory: Replay, batch_size, updates, starting=False):
        states, actions, rewards, next_states, dones = memory.sample(batch_size)

        states = torch.Tensor(states).to(self.device)
        actions = torch.Tensor(actions).to(self.device)
        rewards = torch.Tensor(rewards).to(self.device).unsqueeze(1)
        next_states = torch.Tensor(next_states).to(self.device)
        dones = torch.Tensor(dones).to(self.device).unsqueeze(1)

        with torch.no_grad():
            next_action, next_log_pi, _ = self.actor.sample(next_states)
            next_qf1, next_qf2 = self.critic_target(next_states, next_action)
            # print(torch.min(next_qf1, next_qf2))
            next_qf = torch.min(next_qf1, next_qf2) - self.alpha * next_log_pi
            next_q = rewards + dones * self.gamma * next_qf
        qf1, qf2 = self.critic(states, actions)
        qf1_loss = nn.MSELoss()(qf1, next_q)
        qf2_loss = nn.MSELoss()(qf2, next_q)
        qf_loss = qf1_loss + qf2_loss

        self.critic_optim.zero_grad()
        qf_loss.backward()
        self.critic_optim.step()

        pi, log_pi, _ = self.actor.sample(states)
        qf1_pi, qf2_pi = self.critic(states, pi)
        qf_pi = torch.min(qf1_pi, qf2_pi)
        actor_loss = (
            (self.alpha * log_pi) - qf_pi
        ).mean()  # Jπ = 𝔼st∼D,εt∼N[α * logπ(f(εt;st)|st) − Q(st,f(εt;st))]
        if not starting:
            self.actor_optim.zero_grad()
            actor_loss.backward()
            self.actor_optim.step()
        
        if self.entropy_tune:
            alpha_loss = -(self.log_alpha * (log_pi + self.target_entropy).detach()).mean()

            self.alpha_optim.zero_grad()
            alpha_loss.backward()
            self.alpha_optim.step()

            self.alpha = self.log_alpha.exp()
            alpha_tlogs = self.alpha.clone()
        else:
            alpha_loss = torch.tensor(0.)
            alpha_tlogs = torch.tensor(self.alpha)

        if updates % self.update_interval == 0:
            self.critic_target.load_state_dict(self.critic.state_dict())

        return qf1_loss, qf2_loss, actor_loss, alpha_loss, alpha_tlogs

    def save_models(self, step):
        torch.save(self.actor.state_dict(), f'saves/actor_{step}.ckpt')
        torch.save(self.critic.state_dict(), f'saves/critic1_{step}.ckpt')
        torch.save(self.critic_target.state_dict(), f'saves/critic2_{step}.ckpt')


class Train(Widget):
    def setup(self):
        ttk.Button(self, text="Train", command=self.train).pack(padx=10, pady=10)

    @threaded_callback
    def train(self):
        args = {
            "alpha": 0.2,
            "gamma": 0.99,
            "update_interval": 100,
            "max_torque": 6,
            "batch_size": 64,
            "entropy_tune": True
        }

        state_size = 8
        agent = SAC(state_size, args)
        memory = Replay(4000)
        writer = SummaryWriter()
        start_steps = 200
        total_steps = 0
        updates = 0
        with Env(self.control._system) as env:
            for i in itertools.count(1):
                episode_reward = 0
                episode_steps = 0
                done = False
                starting = False
                state = env.reset()
                self.control._parent.update_targets(*env.target)
                while not done:
                    if start_steps > total_steps:
                        action = np.random.rand(2) * args["max_torque"] * 2 - args["max_torque"]
                        starting = True
                    else:
                        action = agent.select_action(state)
                        starting = False

                    if len(memory) > args["batch_size"]:
                        c1_loss, c2_loss, a_loss, alpha_loss, alpha_logs = agent.update_model(
                            memory, args["batch_size"], updates, starting
                        )
                        writer.add_scalar("loss/critic1", c1_loss, updates)
                        writer.add_scalar("loss/critic2", c2_loss, updates)
                        writer.add_scalar("loss/actor", a_loss, updates)
                        writer.add_scalar("loss/entropy", alpha_loss, updates)
                        writer.add_scalar("temperature/alpha", alpha_logs, updates)
                        updates += 1

                    print(action, total_steps)
                    next_state, reward, done = env.step(float(action[0]), float(action[1]))
                    episode_steps += 1
                    total_steps += 1
                    episode_reward += reward
                    writer.add_scalar('reward/step', reward, total_steps)
                    mask = 0 if done == -1 else done

                    memory.push(state, action, reward, next_state, mask)

                    state = next_state
                print(
                    f"Episode {i}, episode steps {episode_steps}, episode reward {episode_reward}"
                )
                writer.add_scalar('reward/episode', episode_reward, i)

                if total_steps % 300 == 0:
                    agent.save_models(total_steps)
