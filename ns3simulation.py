import numpy as np
import subprocess
import os
import math
from pathlib import Path

class NS3Simulation():

    dataFolder = 'data'
    imagesFolder = 'images'
    programName = './ns3'
    filePrefix = ''
    plotPrefix = ''
    e2eLatHist = None
    process = None
    data = []
    positions = []
    discardedTime = 1.5
    
    def __init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment,path):
        self.gen = gen
        self.scenario = scenario
        self.nUEs = nUEs
        self.neNBs = neNBs
        self.interPacketInterval = interPacketInterval
        if nPackets is not None:
            self.nPackets = nPackets
            self.simTime = int(self.nPackets*self.interPacketInterval + self.discardedTime)
        elif simTime > 0:
            self.nPackets = int(simTime/interPacketInterval)
            self.simTime = simTime + self.discardedTime
        self.radius = radius
        self.height = height
        self.seed = seed
        self.comment = comment
        self.simName = '4G-5G_comparison'
        self.ns3Args =  ' --generation='            + str(gen)                  + \
                        ' --scenario='              + str(scenario)             + \
                        ' --numberOfueNodes='       + str(nUEs)                 + \
                        ' --radius='                + str(radius)               + \
                        ' --height='                + str(height)               + \
                        ' --seed='                  + str(seed)                 + \
                        ' --simTime='               + str(self.simTime)         + \
                        ' --nPackets='              + str(self.nPackets)        + \
                        ' --interPacketInterval='   + str(interPacketInterval)  + \
                        ' --path='                  + str(path)

        if traffic: self.ns3Args += ' --traffic'
        if int(scenario) > 1: self.ns3Args += ' --numberOfenbNodes=' + str(neNBs)
        if comment != '': self.ns3Args += ' --comment=' + comment
        self.rootFolderPath = path
        self.simFolderPath = Path(self.rootFolderPath, self.gen, str(self.nUEs) + ' UEs')
        
    def run(self,gdb=False, forced=False):
        if Path(self.filepath).is_file() and not forced:
            return None

        if gdb:
            self.wafArgs = [self.programName, '--command-template=gdb -ex=r --args %s ' + self.ns3Args, '--run', self.simName]
        else:
            self.wafArgs = [self.programName, 'run', self.simName + " " + self.ns3Args]

        self.checkFolderStructure()
        self.process = subprocess.Popen(self.wafArgs)
        return self.process

    def isRunning(self):
        if self.process == None:
            return False
        else:
            return self.process.poll() == None

    def checkFolderStructure(self):
        path = Path(self.rootFolderPath, self.gen)
        if os.path.isdir(path):
            path = Path(path, str(self.nUEs) + ' UEs')
            if not os.path.isdir(path):
                os.mkdir(path)
            if not os.path.isdir(Path(path, self.dataFolder)):
                os.mkdir(Path(path, self.dataFolder))
            if not os.path.isdir(Path(path, self.imagesFolder)):
                os.mkdir(Path(path, self.imagesFolder))
    
    def parseOutput(self, truncate):
        self.data = []
        self.checkFolderStructure()
        transferFileSuccessfull = False
        positionsFileSuccessfull = False
        
        try:
            with open(self.filepath, 'r') as fp:
                # Parse the rest of the file
                packetNumber = 0
                ueId = 0
                line = fp.readline()
                while line:
                    dataLine = []
                    for n in line.split():
                        dataLine.append(int(n))
                    time = dataLine[1]/1e6
                    if (packetNumber > 1000 and packetNumber < (self.simTime-1)*1000 and time < self.simTime) or not truncate:
                        self.data.append(dataLine)
                    if ueId == dataLine[0]:
                        packetNumber += 1
                    else:
                        packetNumber = 0
                        ueId = dataLine[0]
                    line = fp.readline()
                
                # Sort the data in chronological order
                self.data.sort(key=lambda x: x[1])
                self.nPackets = len(self.data)
                transferFileSuccessfull = True
        except IOError:
            if Path(self.filepath).is_file():
                print("Error occurred opening ", self.filepath)
            else:
                print(self.filepath, ' does not exist')
            transferFileSuccessfull = False
            return False

        filepath_positions = Path(self.simFolderPath, self.dataFolder, self.filePrefix + '_positions.txt')
        self.positions = []

        try:
            with open(filepath_positions, 'r') as fp:
                line = fp.readline()
                while line:
                    self.positions.append(line.split())
                    line = fp.readline()
                positionsFileSuccessfull = True
        except IOError:
            print(filepath_positions, ' does not exist')
            positionsFileSuccessfull = False
            return False

        return transferFileSuccessfull and positionsFileSuccessfull
                            
    
    def calculateE2eLatHist(self, binWidth, highestBin):
        # Create end to end latency vector in milliseconds
        e2eLatency = []
        for t in self.data:
            val = t[2]/1000
            if val > 0:
                e2eLatency.append(val)
            elif val < 0:
                e2eLatency.append(2000)

        # Calculate the number of bins of the histogram
        nBins = int(highestBin/binWidth)

        # Create the histogram from the end to end latency vector, discard the edges
        e2eLatHist, _ = np.histogram(e2eLatency, range=(0, highestBin), bins=nBins)

        # Store the information in the class instance
        self.e2eLatHist = e2eLatHist/self.nPackets

        # Store the number of received packets
        self.receivedPackets = len(e2eLatency)
    
    def calculateCumulativeLat(self, binWidth, highestBin):
        # Check if the latency histogram is populated and populate it if not
        if self.e2eLatHist.all() == None:
            self.calculateE2eLatHist(binWidth, highestBin)

        # Calculate the cumulative latency distribution
        self.cumulativeLat = []
        acc = 0
        for b in self.e2eLatHist:
            acc += b
            self.cumulativeLat.append(acc)

        # Store the information in the class instance
        self.cumulativeLat = np.array(self.cumulativeLat)

    def calculateJitterFunction(self, windowSize, overlap):
        # Calculate the total number of overlapping windows
        nWindows = int(self.simTime/(windowSize/1000*overlap))
        # Initialize the windows nested lists
        windows = []
        for _ in range(nWindows):
            windows.append([])

        # Populate each window with the latency of the packets received in that window
        for p in self.data:
            v = p[1]/(1000*windowSize)
            if v < nWindows:
                windows[int(math.floor(v)*2)].append(p[2])
                v = (p[1] - windowSize*overlap)/(1000*windowSize)
                windows[int(math.floor(v)*2+1)].append(p[2])

        # Calculate the jitter as the standard deviation of the latencies in each window
        self.jitter = []
        for e in windows:
            self.jitter.append(np.std(e)/1000)

    def calculateXCorrJitter(self, windowSize, overlap):
        if self.jitter == None:
            self.calculateJitterFunction(windowSize, overlap)

        jitter = np.array(self.jitter)
        nan_array = np.isnan(jitter)
        jitter = jitter[~ nan_array]

    def calculatePacketStatistics(self, lateTreshold):
        # Sanity check before executing the function
        if self.nPackets == None or self.receivedPackets == None:
            print('Run "parseOutput()" and "calculateE2eLatHist()" before running "calculatePacketStatistics()"')
            return
        
        self.downlinkLatePackets = 0
        self.uplinkLatePackets = 0
        for t in self.data:
            if t[2] == 18446744073709551615:
                self.uplinkLatePackets += 1
            elif t[2] > lateTreshold*1000:
                self.downlinkLatePackets += 1
            

        self.droppedPackets = self.nPackets - self.receivedPackets
        self.rxPercentage = self.receivedPackets / self.nPackets
        self.droppedPercentage = self.droppedPackets / self.nPackets
        self.downlinkLatePercentage = self.downlinkLatePackets / self.nPackets
        self.uplinkLatePercentage = self.uplinkLatePackets / self.nPackets

    def filePrefixNoSeed(self):
        s = self.filePrefix 
        l = s.split(s[s.index('-s'):s.index('-t')])
        return l[0] + l[1]

class NS3LTESimulation(NS3Simulation):

    def __init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment,path):
        NS3Simulation.__init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment,path)
        self.filePrefix = ''
        if int(scenario) > 1: self.filePrefix = 'eNB' + str(neNBs) + '-'
        self.filePrefix += 'r' + str(radius) + '-s' + str(seed) + '-t' + str(self.simTime) + '-' + comment
        self.filepath = Path(self.simFolderPath, self.dataFolder, self.filePrefix + '_transferFile.txt')

class NS3NRSimulation(NS3Simulation):

    def __init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,numerology,seed,comment,path):
        NS3Simulation.__init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment,path)
        self.filePrefix = ''
        if int(scenario) > 1: self.filePrefix = 'gNB' + str(neNBs) + '-'
        self.filePrefix += 'r' + str(radius) + '-num' + str(numerology) + '-s' + str(seed) + '-t' + str(self.simTime) + '-' + comment
        self.filepath = Path(self.simFolderPath, self.dataFolder, self.filePrefix + '_transferFile.txt')
        self.ns3Args += ' --numerology=' + str(numerology)
        self.numerology = numerology
