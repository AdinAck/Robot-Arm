import torch
import torch.functional as F
from torch.distributions import Normal
import torch.nn as nn

epsilon = 1e-6


class Actor(nn.Module):
    def __init__(self, state_size, max_torque):
        super().__init__()

        self.max_torque = max_torque

        self.seq = nn.Sequential(
            nn.Linear(state_size, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
        )
        self.mean_l = nn.Linear(64, 2)
        self.std_l = nn.Linear(64, 2)

    def forward(self, state):
        state = self.seq(state)

        mean = self.mean_l(state)
        std = self.std_l(state)

        return mean, std

    def sample(self, state):
        mean, std = self.forward(state)
        # print(mean, std)
        std = std.exp()
        normal = Normal(mean, std)
        x_t = normal.rsample()
        y_t = torch.tanh(x_t)

        action = y_t * self.max_torque

        log_prob = normal.log_prob(x_t)
        log_prob -= torch.log(
            self.max_torque * (1 - y_t.pow(2)) + epsilon
        )  # not sure why i need this but i do i think
        log_prob = log_prob.sum(1, keepdim=True)

        mean = torch.tanh(mean) * self.max_torque

        return action, log_prob, mean


class QNetwork(nn.Module):
    def __init__(self, state_size):
        super().__init__()

        self.q1 = nn.Sequential(
            nn.Linear(state_size + 2, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

        self.q2 = nn.Sequential(
            nn.Linear(state_size + 2, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, state, action):
        x = torch.cat((state, action), dim=1)

        x1 = self.q1(x)
        x2 = self.q2(x)

        return x1, x2


class VNetwork(nn.Module):
    def __init__(self, state_size):
        super().__init__()

        self.seq = nn.Sequential(
            nn.Linear(state_size, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, state):
        return self.seq(state)
