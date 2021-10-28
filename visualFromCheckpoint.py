import neat
import visualize

config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                             neat.DefaultSpeciesSet, neat.DefaultStagnation,
                             'config-feedforward')

p = neat.Checkpointer.restore_checkpoint('neat-checkpoint-50')

node_names = {-1: 'M2 pos target', -2: 'M2 vel target', -3: 'M3 pos target', -4: 'M3 vel target', -
              5: 'M2 pos current', -6: 'M2 vel current', -7: 'M3 pos current', -8: 'M3 vel current', 0: 'M2 Torque', 1: 'M3 Torque'}
p.run(lambda _: None, 0)
visualize.draw_net(config, p.best_genome, node_names=node_names)