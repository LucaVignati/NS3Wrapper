import time
import copy
from pathlib import Path

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

    def run(self, gdb, forced, wait, nThreads, last):
        for simulation in self.simList:
            self.busyWait(nThreads)
            self.runningSims.append(simulation)
            if not self.dry:
                simulation.run(gdb, forced)
            if wait:
                time.sleep(2)
        if last:
            self.busyWait(1)

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

    def writeAverageSimFiles(self):
        self.data = []
        self.positions = []
        self.avgSim = copy.copy(self.simList[0])
        self.avgSim.filePrefix = self.avgSim.filePrefixNoSeed() + 'avg' + str(len(self.simList))
        self.avgSimFilepath = Path(self.avgSim.simFolderPath, self.avgSim.dataFolder, self.avgSim.filePrefix + '_transferFile.txt')
        self.avgSimFilepathPositions = Path(self.avgSim.simFolderPath, self.avgSim.dataFolder, self.avgSim.filePrefix + '_positions.txt')
        
        #if not self.dry:
        for simulation in self.simList:
            self.data += simulation.data
            self.positions += simulation.positions
        
        self.data.sort(key=lambda x: x[1])
        
        with open(self.avgSimFilepath, 'w') as f:
            for line in self.data:
                f.write(str(line[0]) + ' ' + str(line[1]) + ' ' + str(line[2]) + '\n')
            
        with open(self.avgSimFilepathPositions, 'w') as f:
            for line in self.positions:
                f.write(str(line[0]) + ' ' + str(line[1]) + ' ' + str(line[2]) + ' ' + str(line[3]) + ' ' + str(line[4]) + '\n')

    def getAverageSim(self):
        self.writeAverageSimFiles()
        self.avgSim.parseOutput(truncate=False)
        self.avgSim.calculateE2eLatHist(self.binWidth, self.highestBin)
        self.avgSim.calculateCumulativeLat(self.binWidth, self.highestBin)
        self.avgSim.calculatePacketStatistics(self.lateThreshold)
        return self.avgSim
