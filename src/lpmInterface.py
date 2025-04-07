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

import os, csv, time
import numpy as np
from TLPM import TLPM
from timeit import default_timer as timer
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from PySide6.QtCore import QThread, QObject, Signal, Slot, QEventLoop

from ctypes import c_long, c_ulong, c_uint32, byref, create_string_buffer, c_bool, c_char_p, c_int, c_int16, \
    c_double

from automationThreads import MeasurementManager

import time
import sys

class SensorDevice():
    def __init__(self):
        self.bridge = TLPM()

    def disconnect(self):
        self.bridge.close()
        print("Power meter disconnected")

    def connect(self):
        deviceCount = c_uint32()
        self.bridge.findRsrc(byref(deviceCount))
        print("devices found: " + str(deviceCount.value))
        if deviceCount.value<1:
            print("thorlabs power meter not found")
            exit(-1)

        resourceName = create_string_buffer(1024)
        self.bridge.getRsrcName(c_int(0), resourceName)
        self.bridge.open(resourceName, c_bool(True), c_bool(True))
        print('\nPower meter connected\n')
        return self.bridge

    # def measure(self, wavelength, powerLevel, fileName, duration, avgTime):

    #     # This function performs the power measurement, calling the tlPM device
    #     # The wavelength, average time and duration configure the process
    #     # The set powerlevel is written in the file together with the results
        
    #     thermometer = False
        
    #     self.bridge.setWavelength(c_double(float(wavelength)))
    #     time.sleep(0.1); #Without this delay the first number is consistently higher than the rest

    #     #check if temperature sensor is connected
    #     temperature = c_double()
    #     try:
    #         self.bridge.measExtNtcTemperature(byref(temperature))
    #         thermometer = True
    #     except NameError as err:
    #         print("Temperature sensor not connected! ")
    #         print(err.args)
        
    #     #check if file is empty, if not print headline
    #     origStdOut = sys.stdout
    #     with open(fileName,"a") as fout:
    #         if fout and os.stat(fileName).st_size == 0:
    #             sys.stdout = fout
    #             if not thermometer:
    #                 print("timestamp\twavelength[nm]\tsetting[%]\tpower[mW]")
    #             elif temperature.value != 0:
    #                 print("timestamp\twavelength[nm]\tsetting[%]\tpower[mW]\ttemperature[C]")
    #             sys.stdout = origStdOut
        
    #     start = datetime.now()

    #     measure_until = start + timedelta(seconds=float(duration))
    #     average_until = start
    #     while datetime.now() <= measure_until:

    #         average_count = 0
    #         total_power = 0
    #         total_temperature = 0
            
    #         start_average = datetime.now()  
    #         average_until = start_average + timedelta(seconds=float(avgTime))

    #         while(datetime.now() < average_until):
    #             power = c_double()
    #             self.bridge.measPower(byref(power))
    #             total_power += power.value
        
    #             if thermometer:
    #                 self.bridge.measExtNtcTemperature(byref(temperature))
    #                 total_temperature += temperature.value
    #             average_count += 1
                
    #         total_power /= average_count
    #         total_power = total_power * 1000 # Convert to mW
    #         if thermometer:
    #             total_temperature /= average_count
    #         ts = (start_average-start).total_seconds()

    #         origStdOut = sys.stdout
    #         with open(fileName,"a") as fout:

    #             if thermometer:
    #                 outString = start_average.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + '\t' + str(wavelength) + '\t' + str(powerLevel) + '\t' + str(total_power) + '\t' + str(total_temperature);
    #             else:
    #                 outString = start_average.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + '\t' + str(wavelength) + '\t' + str(powerLevel) + '\t' + str(total_power);
    #             sys.stdout = fout
    #             print(outString)
    #             sys.stdout = origStdOut
    #             print(outString)

    # def measureFast(self, wavelength, duration, avgTime):

    #     # This function performs the power measurement, calling the tlPM device
    #     # The wavelength, average time and duration configure the process
    #     # The set powerlevel is written in the file together with the results

    #     self.bridge.setWavelength(c_double(float(wavelength)))
        
    #     # Increased time delay to prevent initialization errors
    #     time.sleep(0.2)       
    #     results = []

    #     start = datetime.now()
    #     measure_until = start + timedelta(seconds=float(duration))

    #     while datetime.now() <= measure_until:

    #         average_count = 0
    #         total_power = 0
            
    #         start_average = datetime.now()  
    #         average_until = start_average + timedelta(seconds=float(avgTime))
    #         while(datetime.now() < average_until):
    #             power = c_double()
    #             self.bridge.measPower(byref(power))
    #             total_power += power.value
    #             average_count += 1
                
    #         total_power /= average_count

    #         results.append(total_power)
    #     return results
    
class VirtualDevice():
    def __init__(self):        
        self.bridge = self
        self.avgSimulation = 3.5
        self.SimSpan = 0.2

    def disconnect(self):
        print("Power meter disconnected")

    def connect(self):
        deviceCount = 1
        print("Virtual power meter (random number generator)")

class PowerMeter(QObject):
    
    calibrationReady = Signal(object)

    def __init__(self, sensor):
        super().__init__()
        # This calibration table will be associated with a 
        # specific power meter. Mid-term goal: to inquire its serial 
        # number to reload an already-saved calibration
        self.calibrationTable = []
        self.sensor = sensor # A device is PMUSB for instance.        
        self.isCalibrated = False

    def returnStats(self,values):
        self.powerCalibrationPts = values[1][:]
        # print('points: ', self.powerCalibrationPts)
        
        avg   = np.mean(self.powerCalibrationPts)
        noise = np.std(self.powerCalibrationPts)

        print("Average: ",avg,"std: ",noise)
        self.averageSeries.append(avg)
        self.noiseSeries.append(noise)
        if any(value > 0.01 for value in self.noiseSeries):
            print("The data is too noisy to use it as a calibration source")
        else:
            self.calibrationTable = self.calibrate(self.wavelengthSeries, self.averageSeries, self.referenceWavelength)
            print("Calibration table measuring at ",self.referenceWavelength, " mn")
            print("wavelengths: ",self.wavelengthSeries)
            print("Correction factors, returnStats: ", self.calibrationTable)
            self.isCalibrated = True
            self.calibrationReady.emit(self.calibrationTable)
    
    def runCalibrationLoop(self, wavelengthSeries, referenceWavelength, runningMode):
        # We request a short series of measurements or the same source,
        # setting configuring the power meter to different wavelengths
        # The reference Wavelength shoud correspond to the actual wavelength.
        
        self.referenceWavelength = referenceWavelength
        self.wavelengthSeries = wavelengthSeries
        self.averageSeries = []
        self.noiseSeries   = []
        self.calibrationTable = []

        duration   = 5 # 5s measurement by default
        avgTime    = 1 # 1s averaging

        eventLoop = QEventLoop()
        def setMeasComplete():
            eventLoop.quit()

        manager = MeasurementManager(self.sensor, self.returnStats)
        manager.finished.connect(setMeasComplete)

        setpower = 80 # This number is arbitrary, as we are finding ratios only
        mode = runningMode + '-calibration'
        if self.referenceWavelength in self.wavelengthSeries:
            for wavelength in self.wavelengthSeries:
                manager.add_measurement(wavelength, setpower, 'calibration.csv', duration, avgTime, mode)
            manager.start_measurements()
            # Wait until the test peasurements are done
            eventLoop.exec()

        else:
            print("Cannot proceed. \nOne of the set wavelengths must correspond to the source")



    def calibrate(self, lambdaSeries, powerSeries, refLambda):
        # This function builds te array of correction factors when
        # for different wavelengths based on measured values

        # With a monochromatic light source set to certain power 
        # we first run a loop of measurements setting the power 
        # meter device to different wavelength settings. One of 
        # these settings must be correct, while the others will 
        # be for other wavelengths we plan to measure later. This 
        # will allow later to convert powers measured with the 
        # "wrong" wavelength setting into the correct ones.

        lLambda = len(lambdaSeries)

        print('refLambda: ',refLambda)
        print('lambdaSeries: ',lambdaSeries)
        print('powerSeries: ',powerSeries)

        if len(powerSeries) == lLambda:
            self.calibrationTable = []
            self.calibrationTable = np.ones(lLambda)
            try:
                refIndex = lambdaSeries.index(refLambda)
                referencePower = powerSeries[refIndex]
                for wavelengthInd in range(lLambda):
                    if wavelengthInd!=refIndex:               
                        self.calibrationTable[wavelengthInd]= powerSeries[wavelengthInd]/referencePower
                return self.calibrationTable
            except ValueError:
                print("Could not calibrate. \nYour data does not contain the reference wavelength")
                return []
        else:
            print("Error: inconsistent input data")
            return []

def main():

    meterSetWavelength   = 488
    meterSetPowerLevel   = 30
    acquisitionDataFile  = "experiment.csv"
    duration_sec = 5
    avgTime_sec  = 1

    # Acquisition example    
    # PMUSB = VirtualDevice()
    # PMUSB = SensorDevice()    
    # PMUSB.connect()
    # PMUSB.measure(meterSetWavelength, meterSetPowerLevel, acquisitionDataFile, duration_sec, avgTime_sec)
    # PMUSB.disconnect()
    
    # # Calibration example
    # wavelengthSeries = [405, 488, 561, 640]
    # averagePowers = [500, 600, 750, 900]
    # referenceWavelength = 561    
    # #PMUSB = VirtualDevice()
    # PMUSB = SensorDevice()
    # device = PowerMeter(PMUSB)
    # #device.runCalibrationLoop(wavelengthSeries, referenceWavelength, 'test')
    # device.runCalibrationLoop(wavelengthSeries, referenceWavelength, 'system')

if __name__ == "__main__":   
    main()