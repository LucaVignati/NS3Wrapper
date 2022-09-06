from cProfile import label
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np
from pathlib import Path

class Plot():

    imagesFolder = 'images'
    e2eLatHistFileName = '_latencyHistogram.png'
    cumulativeLatFileName = '_latencyCumulative.png'
    jitterFileName = '_jitterFunction.png'
    xcorrFileName = '_jitterXcorr.png'

    def __init__(self, simContainer):
        self.container = simContainer

    def e2eLatency(self, simulation, save=True, holdOn=False):
        """
        Plots the end to end latency histogram
        """
        e2eLatHist = simulation.e2eLatHist
        e2eLatPlotFile = Path(simulation.simFolderPath, self.imagesFolder, simulation.filePrefix + self.e2eLatHistFileName)
        plt.bar(np.linspace(0, self.container.highestBin, self.container.nBins), e2eLatHist, width=self.container.binWidth)
        plt.xlabel('Latency [ms]')
        plt.ylabel('Probability [%]')
        plt.grid(axis='y', alpha=0.75)
        plt.legend([str(simulation.nUEs) + ' UEs - Rx Packets: ' + str(simulation.rxPercentage * 100) + '%'])
        if save:
            plt.savefig(e2eLatPlotFile)
        if not holdOn:    
            plt.close()
    
    def cumulativeLat(self, simulation, save=True, holdOn=False):
        """
        Plots the cumulative latency distribution
        """
        cumulativeLat = simulation.cumulativeLat
        e2eCumLatPlotFile = Path(simulation.simFolderPath, self.imagesFolder, simulation.filePrefix + self.cumulativeLatFileName)
        plt.plot(np.linspace(0, self.container.highestBin, self.container.nBins), cumulativeLat)
        plt.xlabel('Latency [ms]')
        plt.ylabel('CDF [Latency]')
        plt.grid(True, alpha=0.75)
        plt.axis([0, self.container.highestBin, 0, 1])
        plt.legend([str(simulation.nUEs) + ' UEs - Lost (downlink): ' + str(simulation.droppedPercentage * 100) + '%\n' + 
                                                  'Late + lost (uplink)' + str(simulation.uplinkLatePercentage * 100) + '%\n' +
                                                  'Late (downlink)' + str(simulation.downlinkLatePercentage * 100) + '%\n'])
        if save:
            plt.savefig(e2eCumLatPlotFile)
        if not holdOn:    
            plt.close()

    def jitterFunction(self, simulation, save=True, holdOn=False):
        """
        Plots the jitter function of time
        """
        e2eJitPlotFile = Path(simulation.simFolderPath, self.imagesFolder, simulation.filePrefix + self.jitterFileName)
        plt.plot(np.linspace(0, simulation.simTime, len(simulation.jitter)), np.array(simulation.jitter))
        plt.xlabel('Time [s]')
        plt.ylabel('Jitter [ms]')
        plt.grid(True, alpha=0.75)
        plt.axis([0, simulation.simTime, 0, 10])
        plt.legend([str(simulation.nUEs) + ' UEs - Rx Packets: ' + str(simulation.rxPercentage * 100) + '%'])
        if save:
            plt.savefig(e2eJitPlotFile)
        if not holdOn:    
            plt.close()    

    def xCorrJitter(self, simulation, save=True, holdOn=False):
        """
        Plots the autocorrelation function of jitter function
        """
        jitter = simulation.jitter
        n = len(jitter)
        e2eJitPlotFile = Path(simulation.simFolderPath, self.imagesFolder, simulation.filePrefix + self.xcorrFileName)
        plt.plot(np.linspace(0, 2*n, 2*n - 1), np.correlate(np.array(jitter), np.array(jitter), "full"))
        plt.xlabel('Time [s]')
        plt.ylabel('Jitter')
        plt.grid(True, alpha=0.75)
        plt.legend([str(simulation.nUEs) + ' UEs - Rx Packets: ' + str(simulation.rxPercentage * 100) + '%'])
        if save:
            plt.savefig(e2eJitPlotFile)
        if not holdOn:    
            plt.close()

    def nUEsSummaryGraph(self, start, end, seeds):
        legend = []
        c = self.container
        simList = c.simList
        sim = simList[0]
        destFile = Path(sim.rootFolderPath, 'summary', sim.gen + '-' + sim.filePrefix + '_nUEs(' + str(start) + ':' + str(end) + ')SummaryPlot-' + str(c.highestBin) + 'ms.png')
        for s in simList:
            self.cumulativeLat(s, save=False, holdOn=True)
            legend.append(str(s.nUEs) + ' UEs')

        title = sim.gen + ' scenario ' + sim.scenario
        if sim.gen == '5G': title += ' numerology ' + str(sim.numerology)
        title += ' - ' + str(seeds) + ' sims per plot'
        if int(sim.scenario) > 1:
            title += ' - ' + str(sim.neNBs)
            if sim.gen == '4G':
                title += ' eNBs'
            else:
                title += ' gNBs'
        plt.legend(legend)
        plt.title(title)
        plt.savefig(str(destFile))
        plt.close()

    def packetStatistics(self, start, end, pace, seeds):
        uplinkLate = []
        downlinkLate = []
        lost = []
        c = self.container
        ticks = range(start, end + 1, pace)
        simList = c.simList
        sim = simList[0]
        destFile = Path(sim.rootFolderPath, 'statistics', sim.gen + '-' + sim.filePrefix + '_nUEs(' + str(start) + ':' + str(end) + ')StatisticsPlot' + '.png')
        for s in simList:
            uplinkLate.append(s.uplinkLatePercentage)
            downlinkLate.append(s.downlinkLatePercentage)
            lost.append(s.droppedPercentage)


        uplinkLate = np.array(uplinkLate)
        downlinkLate = np.array(downlinkLate)
        lost = np.array(lost)

        fig, ax = plt.subplots()
        x = np.array(range(start, end + 2, pace))
        ax.bar(x, uplinkLate + lost + downlinkLate, width=1, label='Total')
        ax.bar(x - 1/3, uplinkLate, width=1/4, label='Late + lost packets (uplink)')
        ax.bar(x, lost, width=1/4, label='Lost Packets (downlink)')
        ax.bar(x + 1/3, downlinkLate, width=1/4, label='Late packets (downlink)')
        ax.set_xticks(ticks)
        ax.set_xlabel('Number of UEs')
        ax.set_ylabel('Fraction of lost packets')
        ax.set_yscale('log')
        ax.set_ylim([0.00001, 1])
        
        ax.legend(loc='best', fancybox=True)

        title = sim.gen + ' scenario ' + sim.scenario
        if sim.gen == '5G': title += ' numerology ' + str(sim.numerology)
        title += ' - ' + str(seeds) + ' simulations per bar'
        if int(sim.scenario) > 1:
            title += ' - ' + str(sim.neNBs)
            if sim.gen == '4G':
                title += ' eNBs'
            else:
                title += ' gNBs'
        plt.title(title)
        plt.savefig(str(destFile))
        plt.close()

    def positions(self):
        c = self.container
        simList = c.simList
        for sim in simList:
            positions = sim.positions
            marker = ''
            title = 'Positions'
            destFile = Path(sim.simFolderPath, self.imagesFolder, sim.filePrefix + '_positions' + '.png')
            fig, ax = plt.subplots()
            for position in positions:
                x = float(position[1])
                y = float(position[2])
                if position[0] == "eNB" and position[4] == "r":
                    marker = 'ro'
                    circle = plt.Circle((x, y), sim.radius, color='black', fill=False)
                    ax.add_patch(circle)
                if position[0] == "UE" and position[4] == "r":
                    marker = 'bo'
                if position[0] == "eNB" and position[4] == "t":
                    marker = 'co'
                    circle = plt.Circle((x, y), sim.radius, color='black', fill=False)
                    ax.add_patch(circle)
                if position[0] == "UE" and position[4] == "t":
                    marker = 'yo'
                ax.plot(x, y, marker)

            ax.set_aspect('equal', adjustable='box')
            plt.title(title)
            plt.savefig(str(destFile))
            plt.close()

    def everyGraph(self, e2e=False, cumulative=True, jitter=False, xcorr=False):
        for simulation in self.container.simList:
            if e2e:
                self.e2eLatency(simulation)
            if cumulative:
                self.cumulativeLat(simulation)
            if jitter:
                self.jitterFunction(simulation)
            if xcorr:
                self.xCorrJitter(simulation)

