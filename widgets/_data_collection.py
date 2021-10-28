from re import L
from time import time
import pickle
from random import randint
from math import cos, sin, sqrt
from itertools import chain
from typing import Callable
import logging

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

    def train(self, generations=100) -> neat.nn.FeedForwardNetwork:

        # Run for specified number of generations.
        winner = self.population.run(self.eval_genomes, generations)

        # Display the winning genome.
        print('\nBest genome:\n{!s}'.format(winner))

        # Show output of the most fit genome against training data.
        print('\nOutput:')
        winner_net = neat.nn.FeedForwardNetwork.create(winner, self.config)

        #!!!
        inputs = ['M2 pos target', 'M3 pos target', 'M2 pos current', 'M2 vel current', 'M3 pos current', 'M3 vel current']
        outputs = ['M2 Torque', 'M3 Torque']
        node_names = {-(i+1): inputs[i] for i in range(len(inputs))} | {i: outputs[i] for i in range(len(outputs))}

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
        self.model = Model(self.runModel, self.config.neat_config, self.config.checkpoint)
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


    def runModel(self, net: neat.nn.FeedForwardNetwork):
        # logging.getLogger().setLevel(logging.DEBUG)
        for motor in self.control._system.motors.values():
            motor.move(0)
        
        t1, t2 = self.control._system.cartesianToDualPolar(
        self.control.x, self.control.y)
        target: list[float] = [t1, t2]  # [m2p, m3p]
        out: list[float] = [0, 0]  # [m2t, m3t]
        

        total_error = 0
        n_steps = 0
        for trial in range(self.config.trials):
            time_start = time()
            
            t = randint(-157, 157)/100
            r = randint(10, 30)
            self.control.x = r*cos(t)
            self.control.y = r*sin(t)
            t1, t2 = self.control._system.cartesianToDualPolar(
                self.control.x, self.control.y)
            target: list[float] = [t1, t2]  # [m2p, m3p]
            out: list[float] = [0, 0]  # [m2t, m3t]
            while (countdown := self.config.duration - (time() - time_start)) >= 0:
                current = [attr() for attr in self.attrs]
                single_error = sum(abs(t - r) for t, r in zip(target, current))
                # !!! [countdown] +, abs and not ** above here
                out = net.activate(list(chain(target, current)))
                current_x, current_y = self.control._system.dualPolarToCartesian(out[0], out[1])
                fake_error = sqrt((current_x - self.control.x)**2 + (current_y - self.control.y)**2)
                #out = [target[0] - current[0], target[1] - current[1]]
                for i, (motor, val) in enumerate(zip([self.control._system.m2, self.control._system.m3], out)):

                    # no applying torque toward out of bounds
                    threshold = 1.5 if i == 0 else 2.2
                    if abs(val) > threshold and val * motor.position > 0:
                        val = 0
                    val *= 2.5
                    val = clamp(val, -3, 3)
                    val = round(val, 2)
                    motor.move(val)

                
                self.drawArms(self.tar_l1, self.tar_l2, target[0], target[1])
                self.drawArms(self.curr_l1, self.curr_l2, self.control._system.m2.position,
                            self.control._system.m3.position, out)


                n_steps += 1
                total_error += single_error
        logging.debug(f'Average error {total_error / n_steps} with {n_steps=}')
        assert n_steps > 0, 'Cannot have 0 time steps'
        return -total_error / n_steps  # fitness

class TrainApp(Application):
    def __init__(self, root, train_config):
        super().__init__(root)
        self.train_config = train_config
    
    def createWidgets(self):
        super().createWidgets()
        self._data_collection = Trainer(self, self.train_config)
        self.toolsMenu.add_command(
            label='trainer', command=self._data_collection.show)
