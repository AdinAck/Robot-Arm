import torch.nn as nn
import torch
import numpy as np
from collections import namedtuple

Experience = namedtuple('Experience', ('state', 'action', 'reward', 'next_state', 'done'))


class PriorityBuffer:
    def __init__(self, capacity, alpha=0.6, max_priority=1):
        self.capacity = capacity
        self.buffer = []
        self.max_priority = max_priority
        self.position = 0
        self.alpha = alpha
        self.priorities = np.zeros(capacity)

    def __len__(self):
        return len(self.buffer)

    def push(self, experience, priority=None):
        if priority is None:
            priority = self.max_priority
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = experience
        self.priorities[self.position] = priority
        self.position = (self.position + 1) % self.capacity

    
    def sample(self, batch_size, beta=0.4):
        if len(self.buffer) == self.capacity:
            prios = self.priorities
        else:
            prios = self.priorities[:self.position]
        probs = prios ** self.alpha
        probs /= probs.sum()
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        samples = [self.buffer[idx] for idx in indices]
        total = len(self.buffer)
        weights = (total * probs[indices]) ** (-beta)
        weights /= weights.max()
        weights = np.array(weights, dtype=np.float32)
        return samples, indices, weights

    def update_priorities(self, batch_indices, batch_priorities):
        for idx, prio in zip(batch_indices, batch_priorities):
            prio = min(self.max_priority, prio)
            self.priorities[idx] = prio
        
class DQN(nn.Module):
    def __init__(self, input_shape, n_actions):
        super(DQN, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(input_shape, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
        )
        self.value_head = nn.Linear(128, 1)
        self.advantage_head = nn.Linear(128, n_actions)
    
    def forward(self, x):
        x = self.model(x)
        values = self.value_head(x)
        advantages = self.advantage_head(x)
        # fix to include values!
        return advantages

def unpack_batch(batch):
    states, actions, rewards, dones, next_states = [], [], [], [], []
    for exp in batch:
        state = np.array(exp.state, copy=False)
        states.append(state)
        actions.append(exp.action)
        rewards.append(exp.reward)
        dones.append(exp.next_state is None)
        if exp.next_state is None:
            next_states.append(state)       # the result will be masked anyway
        else:
            next_states.append(np.array(exp.next_state, copy=False))
    return np.array(states, copy=False), np.array(actions), np.array(rewards, dtype=np.float32), \
           np.array(dones, dtype=np.uint8), np.array(next_states, copy=False)

def calc_losses(batch, net, tgt_net, gamma, device='cpu', double=True):
    states, actions, rewards, dones, next_states = unpack_batch(batch)

    states = torch.FloatTensor(states).to(device)
    next_states = torch.FloatTensor(next_states).to(device)
    actions = torch.LongTensor(actions).to(device)
    rewards = torch.FloatTensor(rewards).to(device)
    dones = torch.ByteTensor(dones).to(device)

    state_action_values = net(states).gather(1, actions.unsqueeze(-1)).squeeze(-1)
    if double:
        next_state_actions = net(next_states).max(1)[1]
        next_state_values = tgt_net(next_states).gather(1, next_state_actions.unsqueeze(-1)).squeeze(-1)
    else:
        next_state_values = tgt_net(next_states).max(1)[0]
    next_state_values[dones] = 0.0

    expected_state_action_values = next_state_values.detach() * gamma + rewards

    return (state_action_values - expected_state_action_values) ** 2 / 2

def choose_action(advantages, epsilon=0.01):
    # epsilon-greedy
    if np.random.random() < epsilon:
        return np.random.randint(0, len(advantages.flatten()))
    else:
        return advantages.argmax().item()
