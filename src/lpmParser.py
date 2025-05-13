"""    
@author: Nasser Darwish, Institute of Science and Technology Austria

This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import csv, sys, os
import numpy as np

class DataObject:
    def __init__(self):
        
        # In order to parse the process signature pulses on the acquired data 
        # we use a detection threshold. Values above belong to illumination  
        # pulses and values below belong to dark pauses.
        
        self.detectionThreshold = 0
        self.mode = "none"
        self.signature = "none"

        # This flag will be set to true after correcting the power estimations with 
        # the correction factors (will be obtaind using the software).
        self.calibratedValues = False

        # Depending on the order of the pulses the field label 
        # vector will be similar to ["T", "P", "L"]
        self.fieldLabels = []
        self.fieldElemCount = []

        self.timeStamp      = []
        self.wavelength     = []
        self.powerSetting   = []
        self.measuredPower  = []
        
        self.wavelengthArray   = []
        self.powerSettingArray = []
        
        self.dataFile = []
        
        self.timeStampCount     = 0
        self.powerSettingCount  = 0
        self.wavelengthCount    = 0
        self.measuredPowerCount = 0
        self.threshold          = 0

        self.dataObjType = 'unknown'

        # signatures:
        # nPnLnT (power (nP: number of power settings), (nP: number of wavelength settings), (nP: number of time points)) 
        # Examples: Short stability, 4L180T1P [4 wavelengths[180 time points[1 power setting]]]
        #           Long stability, interleaving wavelengths: 1P60T8L [1 power setting[80 itertations[6 wavelengths]]]
        #           3T4L20P [3 time points[4 wavelengths[20 power settings]]]
        # The "none" value will be reserved for a non-initalized system (before user provides input).

        # The container for the values
        self.content = []

    def getFile(self):
        return self.dataFile
    
    def flushFile(self):
        self.dataFile = []        

    def setFile(self,fullFileName):
        self.dataFile = fullFileName
        self.dataObjType = 'file'

    def setmode(self, mode):
        if mode == "auto" or mode == "manual":
            self.mode = mode

    def setSignature(self, signature):
        # This requires structure checkout
        self.signature = signature
        self.parseSignature()

    def getFromFile(self):

        if self.mode == "auto":
            values = self.loadDataByTag()
        if self.mode == "manual":
            values = self.loadDataBySignature()
        return values

    def loadDataByTag(self):
        # Loads the contents of a data file reading the tags
        # the data map self.dataMap[Tidx, Lidx, Pidx]
        # allows the access to each element from the 
        # read indices

        self.fieldLabels = ['T', 'L', 'P']

        timeStampFull     = []
        wavelengthFull    = []
        powerSettingFull  = []
        measuredPowerFull = []

        self.content = self.getFileContent()

        fieldNames = self.content[0]
        dataContent = self.content[1:]

        for filedName in fieldNames:
            print(filedName)
            # find the order:
            try:
                order = [fieldNames.index('timestamp'), \
                         fieldNames.index('wavelength'), \
                         fieldNames.index('setting'), \
                        fieldNames.index('power')]
            except:
                order = [fieldNames.index('timestamp'), \
                         fieldNames.index('wavelength'), \
                         fieldNames.index('setting'), \
                        fieldNames.index('power')]                

        # how many elements:
        for row in dataContent:
            timeStampFull.append(row[order[0]])
            wavelengthFull.append(int(row[order[1]]))
            powerSettingFull.append(int(row[order[2]]))
            measuredPowerFull.append(float(row[order[3]].strip("[]")))

        self.timeStamp     = sorted(list(set(timeStampFull)))
        self.wavelength    = sorted(list(set(wavelengthFull)))
        self.powerSetting  = sorted(list(set(powerSettingFull)))
        self.measuredPower = measuredPowerFull

        # number of different elements
        self.timeStampCount     = len(self.timeStamp)
        self.wavelengthCount    = len(self.wavelength)
        self.powerSettingCount  = len(self.powerSetting)        
        self.measuredPowerCount = len(self.measuredPower)

        print("wavelengths: ",self.wavelength, "; ", self.wavelengthCount, " values")
        print("power settings: ",self.powerSetting, "; ", self.powerSettingCount, " values")

        self.dataMap = np.zeros((self.timeStampCount, 3), dtype=int)

        for element in range(self.measuredPowerCount):
            line = dataContent[element]
            Tidx = self.timeStamp.index(line[0])
            Lidx = self.wavelength.index(int(line[1]))
            Pidx = self.powerSetting.index(int(line[2]))
            self.dataMap[element, :] = [Tidx, Lidx, Pidx]


        #setMetadata(self, lightSourceModel, lightSourceIdentifier)


        print(self.fieldLabels)
        print(self.dataMap.shape)
        print(self.dataMap)

    def reassignData(self, signatureString):
        self.setSignature(signatureString)
        print(signatureString)
        if not self.content == []:
            print("Reassigning...")
            # find all values above threshold

            if self.dataObjType == 'file':
                self.content = self.getFileContent()
                
            elif self.dataObjType == 'stream':
                self.content = [
                    self.timeStamp,
                    self.wavelength,
                    self.powerSetting,
                    self.measuredPower
                ]

            self.dataMap = np.zeros((len(self.content), 3), dtype=int)
            self.parseSignature()

            print('new data map: ', self.dataMap.shape)

            Tidx = self.fieldLabels.index('T')
            Lidx = self.fieldLabels.index('L')
            Pidx = self.fieldLabels.index('P')

            for element in range(len(self.content)):
                self.dataMap[element, : ] = [Tidx, Lidx, Pidx]
        else:
            print("Open data file or start acquisition")    

    def applyThreshold(self):
        print("Applying threshold")
        for index in range(len(self.measuredPower)):
            if self.measuredPower[index] < self.threshold:
                self.measuredPower[index] = 0
            
    def setThreshold(self, threshold):
        self.threshold = threshold
        print("threshold: ", self.threshold)

    def loadDataBySignature(self):
        # Loads the contents of a file using a provided signature

        self.content = self.getFileContent()

        order = [0,1,2,3] # assuming for now [timestamp, wavelength, powersetting, measuredpower]

        # The map will provide the addresses in the readout vector corresponding 
        # to the timestamp, power setting and wavelength indices chosen:
        dataMap = np.zeros(len(self.content),3 ,dtype=int)

        # With this function we get the indices and tags sorted
        self.parseSignature()
        
        Tidx = self.fieldLabels.index('T')
        Lidx = self.fieldLabels.index('L')
        Pidx = self.fieldLabels.index('P')

        for element in range(len(self.content)):
            dataMap[element, : ] = [Tidx, Lidx, Pidx]
        
        print(self.fieldLabels)
        print(dataMap.shape)
        print(dataMap)

    def getFileContent(self):
        self.content = []
        try:
            # CSV, TSV files
            if self.dataObjType == 'file':
                inputSource = self.dataFile
            elif self.dataObjType == 'stream':
                inputSource = sys.stdin

            with open(inputSource) as tsv_file:
                tsvReader = csv.reader(tsv_file, delimiter='\t')
                for row in tsvReader:
                    self.content.append(row)
        except:
            # Other plain text files, including *.txt
            with open(self.dataFile) as textFile:
                for line in textFile:
                    currLine = line.strip()
                    self.content.append(currLine)
        return self.content

    def parseSignature(self):

        positionT = self.signature.find("T")
        positionL = self.signature.find("L")
        positionP = self.signature.find("P")

        labels = ["L", "P", "T"]
        indices = [positionL, positionP, positionT]

        indicesOrig = indices
        
        indices = sorted(indicesOrig)
        permutations = [0,0,0]
        for idx in range(len(permutations)):
            permutations[idx] = indices.index(indicesOrig[idx])

        labels = [item for _, item in sorted(zip(permutations, labels))]

        elemCount = []
        signatureStr = self.signature
        for label in labels:

            parsedContent = signatureStr.split(label)[0]            
            signatureStr = signatureStr.split(label)[1]
            elemCount.append(int(parsedContent))
                
        self.fieldLabels = labels
        self.fieldElemCount = elemCount
        
        print(self.signature)
        print(self.fieldLabels)
        print(self.fieldElemCount)
