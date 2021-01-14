import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np

class Plot():

    imagesFolder = '/images'
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
        e2eLatPlotFile = simulation.simFolderPath + self.imagesFolder + '/' + simulation.filePrefix + self.e2eLatHistFileName
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
        e2eCumLatPlotFile = simulation.simFolderPath + self.imagesFolder + '/' + simulation.filePrefix + self.cumulativeLatFileName
        plt.plot(np.linspace(0, self.container.highestBin, self.container.nBins), cumulativeLat)
        plt.xlabel('Latency [ms]')
        plt.ylabel('ecdf [%]')
        plt.grid(True, alpha=0.75)
        plt.axis([0, self.container.highestBin, 0, 100])
        plt.legend([str(simulation.nUEs) + ' UEs - Rx Packets: ' + str(simulation.rxPercentage * 100) + '%'])
        if save:
            plt.savefig(e2eCumLatPlotFile)
        if not holdOn:    
            plt.close()

    def jitterFunction(self, simulation, save=True, holdOn=False):
        """
        Plots the jitter function of time
        """
        e2eJitPlotFile = simulation.simFolderPath + self.imagesFolder + '/' + simulation.filePrefix + self.jitterFileName
        plt.plot(np.linspace(0, simulation.simTime, self.container.nWindows), np.array(simulation.jitter))
        plt.xlabel('Time [s]')
        plt.ylabel('Jitter [ms]')
        plt.grid(True, alpha=0.75)
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
        e2eJitPlotFile = simulation.simFolderPath + self.imagesFolder + '/' + simulation.filePrefix + self.xcorrFileName
        plt.plot(np.linspace(0, 2*n, 2*n - 1), np.correlate(np.array(jitter), np.array(jitter), "full"))
        plt.xlabel('Time [s]')
        plt.ylabel('Jitter')
        plt.grid(True, alpha=0.75)
        plt.legend([str(simulation.nUEs) + ' UEs - Rx Packets: ' + str(simulation.rxPercentage * 100) + '%'])
        if save:
            plt.savefig(e2eJitPlotFile)
        if not holdOn:    
            plt.close()

    def nUEsSummaryGraph(self, start, end):
        legend = []
        c = self.container
        simList = c.simList
        sim = simList[0]
        destFile = sim.rootFolderPath + 'summary/' + sim.gen + '-' + sim.filePrefix + '_nUEs(' + str(start) + ':' + str(end) + ')SummaryPlot-' + str(c.highestBin) + 'ms.png'
        for s in simList:
            self.cumulativeLat(s, save=False, holdOn=True)
            legend.append(str(s.nUEs) + ' UEs')

        plt.legend(legend)
        plt.savefig(destFile)
        plt.close()

    def packetStatistics(self, start, end):
        statistics = []
        c = self.container
        ticks = range(2, 2*len(c.simList) + 1, 2)
        simList = c.simList
        sim = simList[0]
        destFile = sim.rootFolderPath + 'statistics/' + sim.gen + '-' + sim.filePrefix + '_nUEs(' + str(start) + ':' + str(end) + ')StatisticsPlot' + '.png'
        for s in simList:
            statistics.append(s.rxPercentage * 100)

        plt.bar(range(start, end + 2, 2), statistics)

        plt.xlabel('Number of UEs')
        plt.ylabel('Delivered packets [%]')
        plt.xticks(ticks)
        plt.savefig(destFile)
        plt.close()

    def everyGraph(self, e2e=True, cumulative=True, jitter=True, xcorr=True):
        for simulation in self.container.simList:
            self.e2eLatency(simulation)
            self.cumulativeLat(simulation)
            self.jitterFunction(simulation)
            self.xCorrJitter(simulation)

