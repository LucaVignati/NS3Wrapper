import numpy as np
import argparse
import random
import time
import math
from ns3simulation import NS3Simulation, NS3LTESimulation, NS3NRSimulation
from ns3simulationcontainer import NS3SimulationContainer
from plot import Plot

def instantiateSimulation(args):
    if   args.gen == '4G':
        simulation = NS3LTESimulation(args.gen, args.scenario, args.traffic, args.numberOfueNodes, args.numberOfenbNodes, args.nPackets, 1/args.packetRate, args.simTime, args.radius, args.height, args.seed, args.comment)
    elif args.gen == '5G':
        simulation = NS3NRSimulation(args.gen, args.scenario, args.traffic, args.numberOfueNodes, args.numberOfenbNodes, args.nPackets, 1/args.packetRate, args.simTime, args.radius, args.height, args.numerology, args.seed, args.comment)
    return simulation

parser = argparse.ArgumentParser(description='NS-3 Python wrapper')

parser.add_argument("--gen", choices=["4G", "5G"], required=True, help="5G or 4G")
parser.add_argument("--scenario", choices=["1", "2"], required=True, help="1 or 2")
parser.add_argument("--nUEs", type=int, dest='numberOfueNodes', default=1, help="The number of deployed User Equipments")
parser.add_argument("--neNBs", type=int, dest='numberOfenbNodes', default=2, help="The number of deployed eNBs/gNBs")
parser.add_argument("--nUExCell", type=int, help="The number of deployed UE in each eNBs/gNBs")
parser.add_argument("--time", type=int, dest='simTime', default=6, help="Total simulation time (including start and end times)")
parser.add_argument("--limitPackets", action='store_true', help="Limit the total number of packets for each simulation to that of the shortest simulation")
parser.add_argument("--packets", type=int, dest='nPackets', help="Number of packets transmitted by each UE in each simulation")
parser.add_argument("--packetRate", type=int, default=1500, help="Frequency of packet transmission in Hz")
parser.add_argument("--radius", type=int, dest='radius', default=2, help="Radius of the circle where the UEs are randomly placed")
parser.add_argument("--height", type=float, dest='height', default=1.5, help="Height of the UEs")
parser.add_argument("--num", type=int, dest='numerology', default=2, help="Value defining the subcarrier spaceing and symbol lenght")
parser.add_argument("--seed", type=int, dest='seed', default=0, help="Seed of rand function to use in the simulation")
parser.add_argument("--seeds", type=str, help="Path to file containing the seeds to use. Only relevant if combined with rand")
parser.add_argument("--comment", dest='comment', default='', help="Height of the UEs")
parser.add_argument("--gdb", action='store_true', help="Run the program under gdb")
parser.add_argument("--iterate", nargs=2, help="Specify the interval over which iterate")
parser.add_argument("--dry", action='store_true', help="Runs the script without running the simulator and the plots")
parser.add_argument("--rand", type=int, help="Enables the randomization of seeds and specifies the numer of iteration needed")
parser.add_argument("--threads", type=int, default=1, help="Specifies the maximum number of threads to be used at once")
parser.add_argument("--traffic", action='store_true', dest='traffic', help="Enables the background traffic during the simulations")
parser.add_argument("--maxLat", type=int, dest='highestBin', default=20, help="Specifies the maximum latency displayed in plots")
parser.add_argument("-p", "--plot", action='store_true', dest='plot', help="Enables plot creation for each simulation output")
parser.add_argument("-P", "--plot-summary", action='store_true', dest='plot_summary', help="Enables summary plot creation")
parser.add_argument("--plot-positions", action='store_true', dest='plot_positions', help="Enables the plot of UE and gNB/eNB positions")
parser.add_argument("-f", "--force-rerun", action='store_true', dest='forced', help="Forces every simulation to run, regardless of the presence of previous results overwriting them")


args = parser.parse_args()

if args.scenario == "2": args.numberOfenbNodes = 3

# OOP code
iterate = args.iterate != None
rand = args.rand != None

if iterate:
    it   = args.iterate[0]
    start= int(args.iterate[1].split(':')[0])
    pace = int(args.iterate[1].split(':')[1])
    end  = int(args.iterate[1].split(':')[2])
else:
    start = 0
    pace = 1
    end = 0

if rand:
    seeds = []
    if args.seeds != None:
        with open(args.seeds, 'r') as file:
            for _ in range(args.rand):
                seeds.append(file.readline()[:-1])
    elif args.dry == False:
        for _ in range(args.rand):
            seeds.append(random.randint(1, 1000))

        seedsFile = 'graphs/' + 'summary/' + args.gen + '-Scenario' + str(args.scenario) + '-rand' + str(args.rand) + '.txt'
        with open(seedsFile, 'w') as file:
            for seed in seeds:
                file.write(str(seed) + '\n')
else:
    args.rand = 60

runningSims = []
simContainers = []
simulationContainer = NS3SimulationContainer(args.highestBin, args.dry)
#Instantiate the simulation
for i in range(end, start - 1, -pace):
    if iterate: setattr(args, it, i)
    if args.nUExCell != None: args.numberOfueNodes = args.numberOfenbNodes*args.nUExCell
    if args.limitPackets:
        args.nPackets = int(((4500000+2000*args.numberOfueNodes)/args.rand)/args.numberOfueNodes)
        if args.nPackets < 3000: args.nPackets = 3000
    #print(args.numberOfueNodes, args.nPackets)

    if rand:
        simSeedsContainer = NS3SimulationContainer(args.highestBin, args.dry, runningSims)
        for s in seeds:
            args.seed = s
            simSeedsContainer.add(instantiateSimulation(args))

        if not args.dry:
            simSeedsContainer.run(args.gdb, args.forced, args.threads, i == start)
        
        simContainers.append(simSeedsContainer)

    else:
        simulationContainer.add(instantiateSimulation(args))

for i in range(len(simContainers), 0, -1):
    simContainer = simContainers[i-1]
    simulationContainer.add(simContainer.getAverageSim())
    simulationContainer.simCount += simContainer.simCount
    simulationContainer.simFailed += simContainer.simFailed

    if args.plot:
        plot = Plot(simContainer)
        plot.everyGraph()

# Run the simulation with optional gdb debugger
if not rand:
    simulationContainer.run(args.gdb, args.forced, args.threads, True)

plot = Plot(simulationContainer)

# Parse the output of the simulation and plot the graphs
if args.plot and not rand:
    plot.everyGraph()

if args.plot_summary:
    plot.nUEsSummaryGraph(start, end, args.rand)
    plot.packetStatistics(start, end, pace, args.rand)

if args.plot_positions:
    plot.positions()

print("All simulations ended")
print('Total simulations: ', simulationContainer.simCount + simulationContainer.simFailed)
print('Successful simulations: ', simulationContainer.simCount)
print('Failed simulations: ', simulationContainer.simFailed)
