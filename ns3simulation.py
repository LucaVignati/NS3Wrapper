import numpy as np
import subprocess
import os
import math

class NS3Simulation():

    rootFolderPath = 'graphs/'
    dataFolder = '/data'
    imagesFolder = '/images'
    programName = './waf'
    filePrefix = ''
    plotPrefix = ''
    e2eLatHist = None
    process = None
    data = []
    discardedTime = 1.5
    
    def __init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment):
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
                        ' --interPacketInterval='   + str(interPacketInterval)

        if traffic: self.ns3Args += ' --traffic'
        if int(scenario) > 1: self.ns3Args += ' --numberOfenbNodes=' + str(neNBs)
        if comment != '': self.ns3Args += ' --comment=' + comment
        self.simFolderPath = self.rootFolderPath + self.gen + '/' + str(self.nUEs) + ' UEs'
        
    def run(self,gdb=False):
        if gdb:
            self.wafArgs = [self.programName, '--command-template=gdb -ex=r --args %s ' + self.ns3Args, '--run', self.simName]
        else:
            self.wafArgs = [self.programName, '--run', self.simName + " " + self.ns3Args]

        self.checkFolderStructure()
        self.process = subprocess.Popen(self.wafArgs)
        return self.process

    def isRunning(self):
        if self.process == None:
            return False
        else:
            return self.process.poll() == None

    def checkFolderStructure(self):
        path = self.rootFolderPath + self.gen
        if os.path.isdir(path):
            path += '/' + str(self.nUEs) + ' UEs'
            if not os.path.isdir(path):
                os.mkdir(path)
            if not os.path.isdir(path + self.dataFolder):
                os.mkdir(path + self.dataFolder)
            if not os.path.isdir(path + self.imagesFolder):
                os.mkdir(path + self.imagesFolder)
    
    def parseOutput(self, truncate):
        self.data = []
        self.checkFolderStructure()
        filepath = self.simFolderPath + self.dataFolder + '/' + self.filePrefix + '_transferFile.txt'
        transferFileSuccessfull = False
        positionsFileSuccessfull = False
        
        try:
            with open(filepath, 'r') as fp:
                # Parse the rest of the file
                packetNumber = 0
                ueId = 0
                line = fp.readline()
                while line:
                    dataLine = []
                    for n in line.split():
                        dataLine.append(float(n))
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
                self.data.sort(key=lambda x: x[2])
                self.nPackets = len(self.data)
                transferFileSuccessfull = True
        except IOError:
            print(filepath, ' does not exist')
            transferFileSuccessfull = False

        filepath = self.simFolderPath + self.dataFolder + '/' + self.filePrefix + '_positions.txt'
        self.positions = []

        try:
            with open(filepath, 'r') as fp:
                line = fp.readline()
                while line:
                    self.positions.append(line.split())
                    line = fp.readline()
                positionsFileSuccessfull = True
        except IOError:
            print(filepath, ' does not exist')
            positionsFileSuccessfull = False

        return transferFileSuccessfull and positionsFileSuccessfull
                            
    
    def calculateE2eLatHist(self, binWidth, highestBin):
        # Create end to end latency vector in milliseconds
        e2eLatency = []
        for t in self.data:
            val = t[2]/1000
            if val > 0:
                e2eLatency.append(val)

        # Calculate the number of bins of the histogram
        nBins = int(highestBin/binWidth)

        # Create the histogram from the end to end latency vector, discard the edges
        e2eLatHist, _ = np.histogram(e2eLatency, range=(0, highestBin), bins=nBins)

        # Store the information in the class instance
        self.e2eLatHist = e2eLatHist/len(e2eLatency)

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
        
        self.latePackets = 0
        for t in self.data:
            if t[2] > lateTreshold:
                self.latePackets += 1

        self.droppedPackets = self.nPackets - self.receivedPackets
        self.rxPercentage = self.receivedPackets / self.nPackets
        self.droppedPercentage = self.droppedPackets / self.nPackets
        self.latePercentage = self.latePackets / self.nPackets

    def filePrefixNoSeed(self):
        s = self.filePrefix 
        l = s.split(s[s.index('-s'):s.index('-t')])
        return l[0] + l[1]

class NS3LTESimulation(NS3Simulation):

    def __init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment):
        NS3Simulation.__init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment)
        self.filePrefix = ''
        if int(scenario) > 1: self.filePrefix = 'eNB' + str(neNBs) + '-'
        self.filePrefix += 'r' + str(radius) + '-s' + str(seed) + '-t' + str(self.simTime) + '-' + comment

class NS3NRSimulation(NS3Simulation):

    def __init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,numerology,seed,comment):
        NS3Simulation.__init__(self,gen,scenario,traffic,nUEs,neNBs,nPackets,interPacketInterval,simTime,radius,height,seed,comment)
        self.filePrefix = ''
        if int(scenario) > 1: self.filePrefix = 'gNB' + str(neNBs) + '-'
        self.filePrefix += 'r' + str(radius) + '-num' + str(numerology) + '-s' + str(seed) + '-t' + str(self.simTime) + '-' + comment
        self.ns3Args += ' --numerology=' + str(numerology)
        self.numerology = numerology
