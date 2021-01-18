import time
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import copy

class NS3SimulationContainer():

    simCount = 0
    simFailed = 0

    def __init__(self, highestBin, dry, runningSims=[], binWidth=0.1, windowSize=50, overlap=0.5, lateThreshold=20):
        self.simList = []
        self.runningSims = runningSims
        self.binWidth = binWidth
        self.highestBin = highestBin
        self.nBins = int(self.highestBin/self.binWidth)        
        self.windowSize = windowSize
        self.overlap = overlap
        self.lateThreshold = lateThreshold
        self.dry = dry

    def add(self, simulation):
        self.simList.append(simulation)

    def run(self, gdb, nThreads, last):
        for simulation in self.simList:
            self.busyWait(nThreads)
            self.runningSims.append(simulation)
            if not self.dry:
                simulation.run(gdb)
            time.sleep(0.2)
        if last:
            self.busyWait(1)
        sim = self.simList[0]
        self.nWindows = int(sim.simTime/(self.windowSize/1000*self.overlap))

    def busyWait(self, maxThreads):
        while len(self.runningSims) >= maxThreads:
            for sim in self.runningSims:
                if not sim.isRunning():
                    self.postProcess(sim)
                    self.runningSims.remove(sim)
                time.sleep(0.1)

    def postProcess(self, simulation):
        for _ in range(10):
            simSuccessful = simulation.parseOutput(truncate=True)
            if simSuccessful:
                break
            else:
                time.sleep(0.5)
        if simSuccessful:
            simulation.calculateE2eLatHist(self.binWidth, self.highestBin)
            simulation.calculateCumulativeLat(self.binWidth, self.highestBin)
            simulation.calculateJitterFunction(self.windowSize, self.overlap)
            simulation.calculateXCorrJitter(self.windowSize, self.overlap)
            simulation.calculatePacketStatistics(self.lateThreshold)
            self.simCount += 1
        else:
            self.simFailed += 1

    def writeAverageSimFile(self):
        self.data = []
        self.avgSim = copy.copy(self.simList[0])
        self.avgSim.filePrefix = self.avgSim.filePrefixNoSeed() + 'avg' + str(len(self.simList))
        self.avgSimFilepath = self.avgSim.simFolderPath + self.avgSim.dataFolder + '/' + self.avgSim.filePrefix + '_transferFile.txt'
        
        if not self.dry:
            for simulation in self.simList:
                self.data += simulation.data
            self.data.sort(key=lambda x: x[2])
            
            with open(self.avgSimFilepath, 'w') as f:
                for line in self.data:
                    f.write(str(line[0]) + ' ' + str(line[1]) + ' ' + str(line[2]) + '\n')

    def getAverageSim(self):
        self.writeAverageSimFile()
        self.avgSim.parseOutput(truncate=False)
        self.avgSim.calculateE2eLatHist(self.binWidth, self.highestBin)
        self.avgSim.calculateCumulativeLat(self.binWidth, self.highestBin)
        self.avgSim.calculatePacketStatistics(self.lateThreshold)
        return self.avgSim
