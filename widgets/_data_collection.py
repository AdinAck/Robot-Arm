from re import L
from time import time
import pickle
from random import randint
from math import cos, sin
from itertools import chain
from typing import Callable

from lib.app import Application
import tkinter as tk

import neat
import visualize
from lib.utils import *
from lib.widget import Widget


class Model:
    def __init__(self, eval, config, checkpoint=None):
        self.externalEval = eval
        self.config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                             neat.DefaultSpeciesSet, neat.DefaultStagnation,
                             config)
                        
        # Create the population, which is the top-level object for a NEAT run.
        if checkpoint is not None:
            self.population = neat.Checkpointer.restore_checkpoint(checkpoint)
        else:
            self.population = neat.Population(self.config)
        # Add a stdout reporter to show progress in the terminal.
        self.population.add_reporter(neat.StdOutReporter(True))
        self.stats = neat.StatisticsReporter()
        self.population.add_reporter(self.stats)
        self.population.add_reporter(neat.Checkpointer(1))


    def eval_genomes(self, genomes, config):
        for _, genome in genomes:
            net = neat.nn.FeedForwardNetwork.create(genome, config)
            genome.fitness = self.externalEval(net)

    def train(self, generations=1) -> neat.nn.FeedForwardNetwork:

        # Run for specified number of generations.
        winner = self.population.run(self.eval_genomes, 1)

        # Display the winning genome.
        print('\nBest genome:\n{!s}'.format(winner))

        # Show output of the most fit genome against training data.
        print('\nOutput:')
        winner_net = neat.nn.FeedForwardNetwork.create(winner, self.config)

        node_names = {-1: 'M2 pos target', -2: 'M2 vel target', -3: 'M3 pos target', -4: 'M3 vel target', -
                      5: 'M2 pos current', -6: 'M2 vel current', -7: 'M3 pos current', -8: 'M3 vel current', 0: 'M2 Torque', 1: 'M3 Torque'}
        #p = neat.Checkpointer.restore_checkpoint('neat-checkpoint-50')
        winner = self.population.run(self.eval_genomes, generations)

        visualize.draw_net(self.config, winner, node_names=node_names)
        visualize.plot_stats(self.stats, ylog=False)
        visualize.plot_species(self.stats)

        with open('winner.net', 'wb') as f:
            pickle.dump(winner_net, f)

        return winner_net

    def predict(self) -> list:
        return []


class Trainer(Widget):
    model: Model
    target_duration = .1
    def __init__(self, root, config):
        self.config = config
        super().__init__(root)

    def setup(self):
        self.title("Trainer")

        self.control._system.motorsEnabled(False)

        self.canvas = tk.Canvas(self, width=800, height=600, bg='white')

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

        self.curr_line1 = self.canvas.create_line(0, 0, 0, 0, fill='blue')
        self.curr_line2 = self.canvas.create_line(0, 0, 0, 0, fill='blue')

        self.run()
    
    
    def run(self):
        self.model = Model(self.trainModel, self.config.neat_config, self.config.checkpoint)
        self.model.train(self.config.generations)

    def updateGraph(self, t1, t2):
        x0 = 0
        y0 = 0
        x1 = self.control._system.l1*cos(t1)
        y1 = self.control._system.l1*sin(t1)
        x2 = self.control._system.l2*cos(t1 + t2) + x1
        y2 = self.control._system.l2*sin(t1 + t2) + y1
        self.canvas.move(self.curr_line1, x0, y0, x1, y1)
        self.canvas.move(self.curr_line2, x1, y1, x2, y2)

    def runModel(self, net: neat.nn.FeedForwardNetwork):
        for motor in self.control._system.motors.values():
            motor.move(0)

        t1, t2 = self.control._system.cartesianToDualPolar(
            self.control.x, self.control.y)
        target: list[float] = [t1, 0, t2, 0]  # [m2p, m2v, m3p, m3v]
        out: list[float] = [0, 0]  # [m2t, m3t]

        assert len(target) == len(self.attrs)
        total_error = 0
        time_start = time()
        n_steps = 0
        while (countdown := self.target_duration - (time() - time_start)) >= 0:
            current = [attr() for attr in self.attrs]
            single_error = sum((t - r)**2 for t, r in zip(target, current))
            out = net.activate([countdown] + list(chain(target, current)))
            for motor, val in zip([self.control._system.m2, self.control._system.m3], (round(num, 1) for num in out)):
                motor.move(clamp(val, -2, 2))
            n_steps += 1
            total_error += single_error
        assert n_steps > 0, 'Cannot have 0 time steps'
        return -total_error / n_steps  # fitness

    def trainModel(self, *args, **kwargs):
        t = randint(-157, 157)/100
        r = randint(10, 30)
        self.control.x = r*cos(t)
        self.control.y = r*sin(t)
        return self.runModel(*args, **kwargs)


class TrainApp(Application):
    def __init__(self, root, train_config):
        super().__init__(root)
        self.train_config = train_config
    
    def createWidgets(self):
        super().createWidgets()
        self._data_collection = Trainer(self, self.train_config)
        self.toolsMenu.add_command(
            label='trainer', command=self._data_collection.show)
