from time import time
import pickle
from random import randint
from math import cos, sin
from itertools import chain
from typing import Callable

import tkinter as tk

import neat
import visualize

from lib.widget import Widget


def _compare(a, b):
    assert len(a) == len(b)
    return sum(abs(i - j) for i, j in zip(a, b))


class Model:
    def __init__(self, eval):
        self.externalEval = eval

    def eval_genomes(self, genomes, config):
        for _, genome in genomes:
            net = neat.nn.FeedForwardNetwork.create(genome, config)
            genome.fitness = self.externalEval(net)

    def train(self, config_file) -> neat.nn.FeedForwardNetwork:
        # Load configuration.
        config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                             neat.DefaultSpeciesSet, neat.DefaultStagnation,
                             config_file)

        # Create the population, which is the top-level object for a NEAT run.
        p = neat.Population(config)

        # Add a stdout reporter to show progress in the terminal.
        p.add_reporter(neat.StdOutReporter(True))
        stats = neat.StatisticsReporter()
        p.add_reporter(stats)
        p.add_reporter(neat.Checkpointer(1))

        # Run for up to 300 generations.
        winner = p.run(self.eval_genomes, 1000)

        # Display the winning genome.
        print('\nBest genome:\n{!s}'.format(winner))

        # Show output of the most fit genome against training data.
        print('\nOutput:')
        winner_net = neat.nn.FeedForwardNetwork.create(winner, config)

        node_names = {-1: 'M2 pos target', -2: 'M2 vel target', -3: 'M3 pos target', -4: 'M3 vel target', -
                      5: 'M2 pos current', -6: 'M2 vel current', -7: 'M3 pos current', -8: 'M3 vel current', 0: 'M2 Torque', 1: 'M3 Torque'}
        p = neat.Checkpointer.restore_checkpoint('neat-checkpoint-50')
        winner = p.run(self.eval_genomes, 1)

        visualize.draw_net(config, winner, node_names=node_names)
        visualize.plot_stats(stats, ylog=False)
        visualize.plot_species(stats)

        # p = neat.Checkpointer.restore_checkpoint('neat-checkpoint-4')
        # p.run(eval_genomes, 10)

        with open('winner.net', 'wb') as f:
            pickle.dump(winner_net, f)

        return winner_net

    def predict(self) -> list:
        return []


class Trainer(Widget):
    model: Model
    target_duration = .1

    def setup(self):
        self.title("Trainer")

        self.control._system.motorsEnabled(False)

        self.startButton = tk.Button(self, text='Start')
        self.startButton.pack()

        self.attrs: list[Callable] = [
            lambda: self.control._system.m2.position,
            lambda: self.control._system.m2.velocity,
            lambda: self.control._system.m3.position,
            lambda: self.control._system.m3.velocity,
        ]

        for motor in self.control._system.motors.values():
            motor.setControlMode('torque')
            motor.setPIDs('vel', .2, 20, 0, 0, F=0.01)
            motor.setPIDs('angle', 20, 0, 0, 0, F=0.01)
            motor.move(0)

        self.control._system.motorsEnabled(True)

        self.run()

    def run(self):
        model = Model(self.trainModel)
        model.train('config-feedforward')

    def runModel(self, net: neat.nn.FeedForwardNetwork):
        for motor in self.control._system.motors.values():
            motor.move(0)

        t1, t2 = self.control._system.cartesianToDualPolar(
            self.control.x, self.control.y)

        target: list[float] = [t1, 0, t2, 0]  # [m2p, m2v, m3p, m3v]

        assert len(target) == len(self.attrs)

        out: list[float] = [0, 0]  # [m2t, m3t]

        error = 0

        time_start = time()
        while (countdown := self.target_duration - (time() - time_start)) >= 0:
            current = [attr() for attr in self.attrs]
            single_error = sum((t - r)**2 for t, r in zip(target, current))
            out = net.activate([countdown] + list(chain(target, current)))
            out = [num*2 - 1 for num in out]
            out[0] *= 3
            out[1] *= 2
            for motor, val in zip([self.control._system.m2, self.control._system.m3], (round(num, 1) for num in out)):
                motor.move(val)
            error += single_error

        return -error  # fitness

    def trainModel(self, *args, **kwargs):
        t = randint(-157, 157)/100
        r = randint(10, 30)
        self.control.x = r*cos(t)
        self.control.y = r*sin(t)
        return self.runModel(*args, **kwargs)
