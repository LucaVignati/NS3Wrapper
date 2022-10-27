import numpy as np
import argparse
import random
import time
import math
from ns3simulation import NS3Simulation, NS3LTESimulation, NS3NRSimulation
from ns3simulationcontainer import NS3SimulationContainer
from plot import Plot
from pathlib import Path

def instantiateSimulation(args):
    if   args.gen == '4G':
        simulation = NS3LTESimulation(args.gen, args.scenario, args.traffic, args.numberOfueNodes, args.numberOfenbNodes, args.nPackets, 1/args.packetRate, args.simTime, args.radius, args.height, args.seed, args.comment, root_folder)
    elif args.gen == '5G':
        simulation = NS3NRSimulation(args.gen, args.scenario, args.traffic, args.numberOfueNodes, args.numberOfenbNodes, args.nPackets, 1/args.packetRate, args.simTime, args.radius, args.height, args.numerology, args.seed, args.comment, root_folder)
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
parser.add_argument("--radius", type=int, dest='radius', default=150, help="Radius of the circle where the UEs are randomly placed")
parser.add_argument("--height", type=float, dest='height', default=1.5, help="Height of the UEs")
parser.add_argument("--num", type=int, dest='numerology', default=2, help="Value defining the subcarrier spaceing and symbol lenght")
parser.add_argument("--seed", type=int, dest='seed', default=0, help="Seed of rand function to use in the simulation")
parser.add_argument("--seeds", type=int, help="Trailing number of the summary folder. Only relevant if combined with rand")
parser.add_argument("--comment", dest='comment', default='', help="")
parser.add_argument("--gdb", action='store_true', help="Run the program under gdb")
parser.add_argument("--iterate", nargs=2, help="Specify the interval over which iterate")
parser.add_argument("--dry", action='store_true', help="Runs the script without running the simulator and the plots")
parser.add_argument("--rand", type=int, help="Enables the randomization of seeds and specifies the numer of iteration needed")
parser.add_argument("--threads", type=int, default=1, help="Specifies the maximum number of threads to be used at once")
parser.add_argument("--traffic", action='store_true', dest='traffic', help="Enables the background traffic during the simulations")
parser.add_argument("--max-lat", type=str, dest='highestBin', default="20,50,300", help="Specifies the maximum latency displayed in plots")
parser.add_argument("-p", "--plot", action='store_true', dest='plot', help="Enables plot creation for each simulation output")
parser.add_argument("-P", "--plot-summary", action='store_true', dest='plot_summary', help="Enables summary plot creation")
parser.add_argument("--plot-positions", action='store_true', dest='plot_positions', help="Enables the plot of UE and gNB/eNB positions")
parser.add_argument("-f", "--force-rerun", action='store_true', dest='forced', help="Forces every simulation to run, regardless of the presence of previous results overwriting them")
parser.add_argument("--no-wait", action='store_true', dest='no_wait', help='Disables the waiting times between simulation starts')
parser.add_argument("--path", type=str, default='', help="Path to the root folder where to place graphs and data")
parser.add_argument("--new-seeds", action='store_true', dest='new_seeds', help="Forces the generation of new seeds for the simulations")


args = parser.parse_args()

if args.scenario == "2": args.numberOfenbNodes = 3

seeds_num = 0

if args.path == '':
    root_folder = Path('graphs')
else:
    root_folder = Path(args.path)
    folder_simulations = Path(root_folder, "simulations")
    folder_summary = Path(root_folder, 'summary-' + str(seeds_num))

if not root_folder.exists():
    root_folder.mkdir()
if not folder_simulations.exists():
    folder_simulations.mkdir()
if len(list(root_folder.glob("summary*"))) > 0:
    seeds_num = max([int(filename.name.split("-")[-1]) for filename in root_folder.glob("summary*")]) + 1
if args.seeds is not None:
    seeds_num = args.seeds
folder_summary = Path(root_folder, 'summary-' + str(seeds_num).zfill(2))
folder_summary.mkdir(exist_ok=True)
    

# OOP code
iterate = args.iterate != None
rand = args.rand != None
seeds_file = Path(folder_summary, "Seeds-rand" + str(args.rand) + ".txt")

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
    if seeds_file.exists():
        with open(seeds_file, 'r') as file:
            while True:
                seed = file.readline()[:-1]
                if seed == '': break
                seeds.append(seed)
            args.rand = len(seeds)
    elif args.dry == False:
        for _ in range(args.rand):
            seeds.append(random.randint(1, 1000))

        with open(seeds_file, 'w') as file:
            for seed in seeds:
                file.write(str(seed) + '\n')
else:
    args.rand = 60

args.highestBin = [int(x) for x in args.highestBin.split(',')]

runningSims = []
simContainers = []
simulationContainer = NS3SimulationContainer(args.highestBin[0], args.dry)
#Instantiate the simulation
for i in range(end, start - 1, -pace):
    if iterate: setattr(args, it, i)
    if args.nUExCell != None: args.numberOfueNodes = args.numberOfenbNodes*args.nUExCell
    if args.limitPackets:
        args.nPackets = int(((4500000+2000*args.numberOfueNodes)/args.rand)/args.numberOfueNodes)
        if args.nPackets < 3000: args.nPackets = 3000
    #print(args.numberOfueNodes, args.nPackets)

    if rand:
        simSeedsContainer = NS3SimulationContainer(args.highestBin[0], args.dry, runningSims)
        for s in seeds:
            args.seed = s
            simSeedsContainer.add(instantiateSimulation(args))

        if not args.dry:
            simSeedsContainer.run(args.gdb, args.forced, not args.no_wait, args.threads, i == start)
        
        simContainers.append(simSeedsContainer)

    else:
        simulationContainer.add(instantiateSimulation(args))

for highestBin in args.highestBin:

    if rand:
        simulationContainer = NS3SimulationContainer(highestBin, args.dry)

    for i in range(len(simContainers), 0, -1):
        simContainer = simContainers[i-1]
        simulationContainer.add(simContainer.getAverageSim(highestBin))
        simulationContainer.simCount += simContainer.simCount
        simulationContainer.simFailed += simContainer.simFailed

        if args.plot:
            for simCont in simContainers:
                plot = Plot(simCont)
                plot.everyGraph()
        
        if args.plot_positions:
            for simCont in simContainers:
                plot = Plot(simCont)
                plot.positions()

    # Run the simulation with optional gdb debugger
    if not rand:
        simulationContainer.run(args.gdb, args.forced, not args.no_wait, args.threads, True)

    plot = Plot(simulationContainer)

    # Parse the output of the simulation and plot the graphs
    if args.plot and not rand:
        plot.everyGraph()

    if args.plot_summary:
        plot.nUEsSummaryGraph(start, end, args.rand, seeds_num)
        plot.packetStatistics(start, end, pace, args.rand, seeds_num)

    if args.plot_positions and not rand:
        plot.positions()

print("All simulations ended")
print('Total simulations: ', simulationContainer.simCount + simulationContainer.simFailed)
print('Successful simulations: ', simulationContainer.simCount)
print('Failed simulations: ', simulationContainer.simFailed)
