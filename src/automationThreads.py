"""    
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

from PySide6.QtCore import QThread, QObject, Signal, Slot, QEventLoop
from ctypes import c_long, c_ulong, c_uint32, byref, create_string_buffer, c_bool, c_char_p, c_int, c_int16, \
    c_double, sizeof, c_voidp
import time
import sys
from datetime import datetime, timedelta
import os, csv
import numpy as np
from queue import Queue

class Worker(QObject):
    finished = Signal()    
    resultReady = Signal(object)

    def __init__(self, sensor, wavelength, power, fileName, duration, avgTime, runningMode, effect):
        super().__init__()
        self.sensor = sensor
        self.bridge = sensor.bridge
        self.wavelength = wavelength
        self.power = power
        self.fileName = fileName
        self.duration = duration
        self.avgTime = avgTime
        self.runningMode = runningMode
        self.calledFunction = effect
        self.stopRequested = False

        self.results = []

    def returnFileName(self):
        return self.fileName

    def stop(self):
        print(f"Stop requested for wavelength {self.wavelength}.")
        self.stopRequested = True

    def getResults(self):
        return self.results

    @Slot()
    def run(self):
        print(f"Worker started for wavelength {self.wavelength}, power {self.power}")
        try:
            iterations = []
            timePoints = []
            powers = []
        
            # Simulating task execution
            print(f"Running {self.runningMode}")

            if self.runningMode == 'test-standard':
            
                self.avgSimulation = 3.5
                self.SimSpan = 10
                origStdOut = sys.stdout

                with open(self.fileName, "a") as fout:
                    if fout and os.stat(self.fileName).st_size == 0:
                        sys.stdout = fout
                        print("timestamp\twavelength\tpower\ttemperature")
                        sys.stdout = origStdOut

                start = datetime.now()
                measure_until = start + timedelta(seconds=float(self.duration))

                while datetime.now() <= measure_until:
                    average_count = 0
                    total_power = 0
                    start_average = datetime.now()
                    average_until = start_average + timedelta(seconds=float(self.avgTime))

                    while datetime.now() < average_until:
                        power = np.random.normal(self.avgSimulation, self.SimSpan, size=1)
                        total_power += power[-1]
                        average_count += 1
                    if self.stopRequested:
                        break

                    total_power /= average_count
                    origStdOut = sys.stdout

                    with open(self.fileName, "a") as fout:
                        timeString = start_average.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        outString = f"{timeString}\t{self.wavelength}\t{self.power}\t{total_power}"
                        sys.stdout = fout
                        print(outString)
                        sys.stdout = origStdOut
                        print(outString)

                        timePoints.append(timeString)
                        powers.append(total_power)

                        self.results = [timePoints, powers]
                        
                        # This function (to update plots) is expected to run every
                        # time a new value is acquired

                        self.calledFunction(self.results)

            elif self.runningMode == 'system-standard':

                self.sensor.connect()
                thermometer = False
                
                self.sensor.bridge.setWavelength(c_double(float(self.wavelength)))
                temperature = c_double()
                try:                    
                    self.sensor.bridge.measExtNtcTemperature(byref(temperature))
                    thermometer = True
                except NameError as err:
                    print("Temperature sensor not connected!")
                    print(err.args)

                origStdOut = sys.stdout
                with open(self.fileName, "a") as fout:
                    if fout and os.stat(self.fileName).st_size == 0:
                        sys.stdout = fout
                        if not thermometer:
                            print("timestamp\twavelength\tpower")
                        elif temperature.value != 0:
                            print("timestamp\twavelength\tpower\ttemperature")
                        sys.stdout = origStdOut
                
                time.sleep(0.5)  # Without this delay, the first number is consistently higher than the rest
                start = datetime.now()
                measure_until = start + timedelta(seconds=float(self.duration))

                ind = 0 # To discard the first point
                
                counter = 0
                while datetime.now() <= measure_until:
                    average_count = 0
                    total_power = 0
                    total_temperature = 0

                    start_average = datetime.now()
                    average_until = start_average + timedelta(seconds=float(self.avgTime))

                    while datetime.now() < average_until:
                        power = c_double()                        
                        self.sensor.bridge.measPower(byref(power))
                        total_power += power.value * 1000 # W -> mW

                        if thermometer:
                            self.bridge.measExtNtcTemperature(byref(temperature))
                            total_temperature += temperature.value
                        average_count += 1

                    if self.stopRequested:
                        break

                    total_power /= average_count
                    counter = counter + 1
                    
                    if thermometer:
                        total_temperature /= average_count

                    with open(self.fileName, "a") as fout:
                        if thermometer:
                            outString = f"{start_average.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\t{self.wavelength}\t{self.power}\t{total_power}\t{total_temperature}"                            
                        else:
                            outString = f"{start_average.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\t{self.wavelength}\t{self.power}\t{total_power}"                        
                            
                        sys.stdout = fout
                        # With the TLPM sensor the first readont is always slightly off
                        if ind > 0:
                            print(outString)
                            sys.stdout = origStdOut
                            print(outString)
                        
                            timeString = start_average.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                            timePoints.append(timeString)
                            powers.append(total_power)

                            self.results = [timePoints, powers]

                            # This function (to update plots) is expected to run every 
                            # time a new value is acquired
                            self.calledFunction(self.results)
                        ind = ind+1
                self.sensor.disconnect()
                print(f"Worker completing for wavelength {self.wavelength}.")

            elif self.runningMode == 'test-calibration':
                # This function performs the power measurement, calling the tlPM device
                # The wavelength, average time and duration configure the process
                # The set powerlevel is written in the file together with the results

                self.avgSimulation = 3.5
                self.SimSpan = 2

                time.sleep(0.5)  # Without this delay, the first number is consistently higher than the rest
                start = datetime.now()

                measure_until = start + timedelta(seconds=float(self.duration))
                print("Running simulation for a set wavelength of "+ str(self.wavelength)+" nm")

                iteration = 0
                while datetime.now() <= measure_until:

                    average_count = 0
                    total_power = 0

                    start_average = datetime.now()  
                    average_until = start_average + timedelta(seconds=float(self.avgTime))
                    while(datetime.now() <= average_until):
                        power = np.random.normal(self.avgSimulation, self.SimSpan, size = 1)
                        total_power += power[-1]
                        average_count += 1
                    if self.stopRequested:
                        break
                    total_power /= average_count            
                    
                    iterations.append(iteration)
                    powers.append(total_power)

                    self.results = [iterations, powers]  
                    # print('results: ',self.results)                  
                    iteration += 1                   
                # This function (the calibration) is expected to run 
                # once all values are acquired
                self.output = self.calledFunction(self.results)


            elif self.runningMode == 'system-calibration':
                # This function performs the power measurement, calling the tlPM device
                # The wavelength, average time and duration configure the process
                # The set powerlevel is written in the file together with the results
                self.sensor.connect()
                start = datetime.now()

                measure_until = start + timedelta(seconds=float(self.duration))
                print("System mode, set wavelength: "+ str(self.wavelength)+" nm")
                self.bridge.setWavelength(c_double(float(self.wavelength)))
                
                iteration = 0

                while datetime.now() <= measure_until:

                    average_count = 0
                    total_power = 0
                    
                    start_average = datetime.now()  
                    average_until = start_average + timedelta(seconds=float(self.avgTime))
                    while datetime.now() < average_until:
                        power = c_double()
                        self.bridge.measPower(byref(power))
                        total_power += power.value
                        average_count += 1
                    if self.stopRequested:
                        break    
                    total_power /= average_count            
                    
                    iterations.append(iteration)
                    powers.append(total_power)
                    self.results = [iterations, powers]    
                    iteration += 1

                # This function (the calibration) is expected to run 
                # once all values are acquired
                self.output = self.calledFunction(self.results)
                self.sensor.disconnect()
                print(f"Worker completing for wavelength {self.wavelength}.")

        except Exception as e:
            print(f"Error in Worker: {e}")
            self.finished.emit()

        finally:
            print(f"Worker finishing for wavelength {self.wavelength}.")            
            self.finished.emit()

class MeasurementManager(QObject):
    finished = Signal()

    def __init__(self, device, effect):
        super().__init__()
        self.queue = Queue()
        self.device = device
        self.current_thread = None
        self.externalCall = effect
        self.calibrationTable = []
        self.results = []
        self.threadList = []

    def returnFileNames(self):
        fileNameList = []
        for job in self.threadList:    
            _, currWorker = job
            fileNameList.append(currWorker.returnFileName())
        return fileNameList

    def add_measurement(self, wavelength, power, fileName, duration, avgTime, runningMode):
        self.queue.put((wavelength, power, fileName, duration, avgTime, runningMode))
        print(f"Measurement queued: {wavelength}, {power}")

    def start_measurements(self):
        if not self.queue.empty():
            self.process_next_measurement()

    def process_next_measurement(self):
        if not self.queue.empty():
            measurement = self.queue.get()
            wavelength, power, fileName, duration, avgTime, runningMode = measurement
            self.process_measurement(wavelength, power, fileName, duration, avgTime, runningMode)

    def storeResult(self, result):
        self.results.append(result)

    def process_measurement(self, wavelength, power, fileName, duration, avgTime, runningMode):
        print('Processing measurement...')
        thread = QThread()        
        worker = Worker(self.device, wavelength, power, fileName, duration, avgTime, runningMode, self.externalCall)
        worker.moveToThread(thread)
        self.threadList.append((thread, worker))
        
        # Connect signals
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda: self.onWorkerFinished(thread, worker))
        thread.started.connect(worker.run)
        thread.finished.connect(lambda: self.cleanup_thread(thread))
        worker.resultReady.connect(self.storeResult)

        print(f'Starting thread for measurement {wavelength}')
        self.current_thread = thread
        self.current_thread.start()
        return thread

    def onWorkerFinished(self, thread, worker):
        print(f"Worker finished signal received for wavelength {worker.wavelength}.")
        self.calibrationTable = worker.getResults()
        worker.deleteLater()
        self.cleanup_thread(thread)
        self.process_next_measurement()

    def finishThreads(self):        
        for thread, worker in self.threadList:
            print("trying to stop")
            worker.stop()
            thread.quit()
            thread.wait()
            
    def cleanup_thread(self, thread):
        if thread.isFinished():
            print("Cleaning up thread...")            
            thread.deleteLater()
            self.finished.emit()
