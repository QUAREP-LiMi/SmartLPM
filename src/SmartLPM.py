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
    along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import sys, os, csv
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QMainWindow, QMenuBar, QMenu, QPushButton, QDoubleSpinBox, 
    QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QComboBox, QLineEdit, 
    QGroupBox, QSpinBox, QApplication, QSlider, QFileDialog, QLayout, QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt, QUrl, Signal, QEventLoop
from PySide6.QtGui import QDesktopServices, QIcon, QAction

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

from colorhandling import ColorHandler
from lpmInterface import VirtualDevice, SensorDevice, PowerMeter, MeasurementManager
from lpmParser import DataObject
from customGUI import Aesthetics, ListSelect, PushPopList, InputBox, FileAccessWidgt
from fileInterface import TSVAccess



class DataCanvas(FigureCanvasQTAgg):
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):       
        fig = Figure(figsize=(width, height), dpi=dpi, layout='constrained')
        self.axes = fig.add_subplot(111, facecolor='black')
        super(DataCanvas, self).__init__(fig)
    
    def redraw(self,xData,yData):
        self.axes.clear()
        for ind in range(len(yData)):
            if ind == 0:
                self.axes.plot(xData,yData[ind],'white')
            else:
                self.axes.plot(xData,yData[ind],color='gray', linestyle='dashed')
        self.draw()

    def drawOnTop(self,xData,yData, plotColor):
        wavelengthCount = len(yData)
        for wavelength in range(wavelengthCount):
            self.axes.plot(xData,yData[wavelength],color=plotColor)
        self.draw()

    def addSinglePlot(self,xData,yData, plotColor):
        self.axes.plot(xData,yData,color=plotColor)        
        self.draw()

class DataSignature():

    def __init__(self):        
        self.signature = []
        self.signatureString = []
        
    def calculateColors(self, wavelengths):
        # To define how wavelengths will be represented later
        self.Red   = []
        self.Green = []
        self.Blue  = []
        for wavelength in wavelengths:        
            RL, GL, BL = ColorHandler.waveLengthToRGB(wavelength)            
            self.Red.append(RL)
            self.Green.append(GL)
            self.Blue.append(BL)

    def calculateSignature(self):
        # The full signature consists in power setting blocks concatenated

        self.calculateColors(self.wavelengths)

        self.wavelengthCount   = len(self.wavelengths)
        self.powerSettingCount = len(self.setPowers)
        pulsesPerBlock = self.powerSettingCount * self.wavelengthCount
        
        duration = self.duration-self.signaturePause # We want to prepend one section of zeros atr the beggining
        self.readoutCount = int((duration / self.readoutInterval) + 1)

        # The signature initialization works equally for both cases:
        self.signature  = np.zeros((self.wavelengthCount,self.readoutCount))

        self.runingTimePerPulse = int(self.measurementInterval/pulsesPerBlock)
        dataPointsPerPulse = int((self.runingTimePerPulse - self.signaturePause) / self.readoutInterval)
        idlePointsPerPulse = int(self.signaturePause / self.readoutInterval)

        PulselLen = dataPointsPerPulse + idlePointsPerPulse

        overallPulseShift = idlePointsPerPulse  # Start after one idle cycle

        # a block consits in the set of pulses and pauses covering all the 
        # desired cases once. Blocks can be repeated it duration allows        
        blocks = int(duration/self.measurementInterval)

        if self.order == 'LP':
            # Powers first
            
            placeholder = []
            
            # the placeholder defines the signature to repeat for every
            for setPowerInd in range(self.powerSettingCount):
                for readout in range(dataPointsPerPulse):
                    placeholder.append(self.setPowers[setPowerInd])
                for readout in range(idlePointsPerPulse):
                    placeholder.append(0)
            
            lblk = self.wavelengthCount*len(placeholder)
            blockSignature = np.zeros((self.wavelengthCount, lblk))
            # For each wavelegth indices start with an offset
            for wavelengthInd in range(self.wavelengthCount):
                indexZero = wavelengthInd * len(placeholder)
                blockSignature[wavelengthInd, indexZero:indexZero+len(placeholder)] = placeholder

            # repeat the full process for evey block
            for block in range(blocks):
                for wavelengthInd in range(self.wavelengthCount):
                    
                    self.signature[wavelengthInd, block*lblk+overallPulseShift:(block+1)*lblk+overallPulseShift] = blockSignature[wavelengthInd, :]
            
            self.signatureString = str(dataPointsPerPulse)+'T'+str(self.powerSettingCount)+'P'+str(self.wavelengthCount)+'L'

        if self.order == 'PL':
            # Wavelengths first
            
            # Each pulse:
            PulselLen = dataPointsPerPulse + idlePointsPerPulse
            # One pulse per wavelength
            wavelengthSetLen = self.wavelengthCount*PulselLen
            miniblockSignature = np.zeros((self.wavelengthCount, wavelengthSetLen))

            for wavelengthInd in range(self.wavelengthCount):
                start = wavelengthInd * PulselLen
                end   = (wavelengthInd+1) * PulselLen
                for readout in range(start,end):
                    if readout - start < dataPointsPerPulse:
                        miniblockSignature[wavelengthInd,readout] = 1
                        
            lblk = wavelengthSetLen * self.powerSettingCount
            for setPowerInd in range(self.powerSettingCount):
                startP = overallPulseShift  + setPowerInd       * wavelengthSetLen 
                endP   = overallPulseShift  + (setPowerInd + 1) * wavelengthSetLen                
                self.signature[:, startP:endP] = self.setPowers[setPowerInd]*miniblockSignature
                
            for block in range(blocks):
                start = block * lblk
                end   = (block+1) * lblk
                if (end < self.readoutCount):
                    self.signature[:, start:end] = self.signature[:, 0:lblk]
            
            self.signatureString = str(dataPointsPerPulse)+'T'+str(self.wavelengthCount)+'L'+str(self.powerSettingCount)+'P'
            self.structuredData = np.zeros((self.readoutCount, self.wavelengthCount,  self.powerSettingCount))

    def setParameters(self, wavelengths, setPowers, measurementInterval, readoutInterval, duration, signaturePause, order):
        self.wavelengths = wavelengths
        self.setPowers   = setPowers
        self.measurementInterval = measurementInterval
        self.readoutInterval = readoutInterval     
        self.duration = duration
        self.signaturePause = signaturePause
        self.order = order

class CalibrationWindow(QWidget):
    # Accessory window for the interactive calibration of the measurements

    def __init__(self, testMode, listedWavelengths, effect):
        super().__init__()
        self.setWindowIcon(QIcon(os.path.dirname(__file__)+"/Resource/logo.png"))

        self.calibrationFactors = [] 
        self.function = effect
        self.testMode = testMode 
        self.calibrationWavelengths = ['empty']
        self.setWavelength = listedWavelengths
        self.setWindowTitle("Measurement calibration")
        layout = QGridLayout()

        # Widgets
        self.calibrationWidget = PushPopList('Wavelengths considered', 'nm',self.updateList)
        self.setWavelengthSel = ListSelect('Select set wavelength', self.calibrationWavelengths,
                                           self.calibrationWavelengths, self.setCentralWavelength)
        self.startCalibrationBtn = QPushButton("Calibrate", self)
        
        self.startCalibrationBtn.clicked.connect(self.function)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, len(listedWavelengths))

        # Configure window
        layout.addWidget(self.calibrationWidget, 0,0)
        layout.addWidget(self.setWavelengthSel, 1,0)
        layout.addWidget(self.progressBar, 2,0)
        layout.addWidget(self.startCalibrationBtn, 2,1)
        self.setLayout(layout)

        # Initialize the list with the experiment defined
        for inputWavelength in self.setWavelength:
            self.calibrationWidget.inputBox.setText(str(inputWavelength))
            self.calibrationWidget.addElement()

    def closeEvent(self, event):
        return self.setWavelength, self.calibrationFactors

    def setCentralWavelength(self):        
        print(self.setWavelengthSel.currChoice)
        self.setWavelength = self.setWavelengthSel.currChoice

    def updateList(self):
        # Updates the list for selecting a central wavelength
        self.calibrationWavelengths = self.calibrationWidget.list
        self.setWavelengthSel.choices = self.calibrationWavelengths
        self.setWavelengthSel.listDisplay.clear()
        items = []
        for element in self.calibrationWavelengths:
            items.append(str(element))
            print(items)
        self.setWavelengthSel.listDisplay.addItems(items)
        self.setWavelengthSel.listDisplay.setCurrentIndex(len(self.setWavelengthSel.choices)-1)

class programGUI(QMainWindow):
    # Main program window

    def __init__(self, testMode, *args, **kwargs):

        super(programGUI, self).__init__(*args, **kwargs)
        
        # Initialization
        self.testMode = testMode
        if self.testMode == True:
            PMUSB = VirtualDevice()
        else:
            PMUSB = SensorDevice()
        
        self.device = PowerMeter(PMUSB)        
        self.acquiringNow = False        
        self.fieldNames = [
            "wavelengths",
            "setPowers",
            "duration",
            "measurementInterval",
            "averageInterval",
            "readoutInterval",            
            "signaturePause",
            "order"]

        self.defaultDataPath  = os.path.join(os.path.dirname(__file__),"Data")
        self.settingsFilePath = os.path.join(os.path.dirname(__file__),"Config")
        self.configFile = "process.tsv"
        
        self.data = DataObject()
        
        self.wavelengths = []
        self.setPowers   = []
        self.calibrationFactors = []
        self.calibratedWavelengths = []
        self.calibrationConsistency = False #True when calibrated wavelengths match the ones listed for measurement

        # How to handle plots: automatic 
        # reassignment and correction 
        self.dynReassignment = False
        self.dynCorrection   = False
        
        self.dataWasReassigned   = False
        self.dataWasRecalibrated = False

        self.policy = 'blind'
        self.setOffset = 0

        self.signature = DataSignature()
        self.offset = 0
        # Looking good is important!
        self.setWindowIcon(QIcon(os.path.dirname(__file__)+"/Resource/logo.png"))
        
        if testMode == True:
            self.setWindowTitle("QUAREP Semiautomatic Light Power Measurement (test mode)")
        else:
            self.setWindowTitle("QUAREP Semiautomatic Light Power Measurement ")

        self.resize(1000, 700)

        self.timeStamps = np.array([])
        self.powerDataValues = np.array([])
        self.acquiredData = np.array(())

        self.dataLength = len(self.acquiredData)
        self.thresholdLine = np.zeros(self.dataLength)
                     
        # Setup panel .....................................................
        # Here experiments will be configured: Wavelength list, type
        # order of the measurements and time intervals
        # .................................................................
        self.SetupPanel = QWidget(self)
        self.SetupPanelLayout = QGridLayout()
        
        self.SetupPanel.setLayout(self.SetupPanelLayout)

        self.inputBoxesLayout = QGridLayout()
        self.selectorLayout  = QGridLayout()

        self.setupPanelTitle = QLabel("Setup acquisition")
        self.setupPanelTitle.setStyleSheet(Aesthetics.titleBar)

        self.durationInput = InputBox('Duration','s', self.updateDurationAndReplot)
        self.measurementIntervalInput = InputBox('Acquisition interval','s', self.updateAcquisitionRateAndReplot)        
        self.readoutIntervalInput = InputBox('sample interval','s', self.updateReadoutIntervalAndReplot)        
        self.signaturePauseInput = InputBox('signature pause','s', self.updateSignaturePauseAndReplot)        
        # Order selection ...........        
        self.orderChoices     = ['LP', 'PL']
        self.orderChoiceNames = ['wavelengths(powers)', 'powers(wavelengths)']
        self.orderSettingWidget = ListSelect('Acquisition', self.orderChoices, self.orderChoiceNames, self.updateOrderAndReplot)        
        self.orderSettingWidget.listDisplay.setFixedWidth(150)
        # Wavelength & power setting ...........
        self.wavelengthWidget = PushPopList('wavelengths:','nm', self.updateWavelengthsAndReplot)        
        self.powerSettingWidget = PushPopList('power setting:','%', self.updatePowersAndReplot)
        
        self.setupFileWdgt = FileAccessWidgt('Process file', "", "Setup files (*.csv *tsv *.txt)", self.setupFromFile, self.saveSetupToFile)

        for box in [self.durationInput, self.readoutIntervalInput, 
                    self.signaturePauseInput,self.measurementIntervalInput]:
            box.layout.setSpacing(20)
            box.titleLbl.setFixedWidth(120)
            box.inputEdit.setFixedWidth(70)
        
        self.orderSettingWidget.setFixedWidth(350)
        for widget in [self.wavelengthWidget, self.powerSettingWidget]:            
            widget.setFixedWidth(350)
            widget.combo_box.setFixedWidth(50)
            widget.addButton.setFixedWidth(60)
            widget.deleteButton.setFixedWidth(60)
            widget.inputBox.setFixedWidth(70)
            widget.showList.setFixedWidth(200)

        # Figure placeholder for signature schemes:        
        self.SignatureCanvas = DataCanvas(self)

        # To initialize the widgets and data ignature from a file
        self.setupFromFile(self.configFile)
                
        # The elements on the panel
        titleSpanH = 1
        titleSpanV = 2
        settingSpanH = 1
        settingSpanV = 1
        graphRowSpan = 4
        graphColSpan = 2

        self.SetupPanelLayout.addWidget(self.setupPanelTitle, 0,0, titleSpanH, titleSpanV)
        
        self.inputBoxesLayout.addWidget(self.durationInput, 0,0)
        self.inputBoxesLayout.addWidget(self.measurementIntervalInput, 1,0)
        self.inputBoxesLayout.addWidget(self.readoutIntervalInput, 2,0)
        self.inputBoxesLayout.addWidget(self.signaturePauseInput, 3,0)
        
        self.selectorLayout.addWidget(self.orderSettingWidget,0,0,settingSpanV,settingSpanH)
        self.selectorLayout.addWidget(self.wavelengthWidget,1,0,settingSpanV,settingSpanH)
        self.selectorLayout.addWidget(self.powerSettingWidget,2,0,settingSpanV,settingSpanH)

        self.SetupPanelLayout.addLayout(self.selectorLayout,1,0,4,1)
        self.SetupPanelLayout.addLayout(self.inputBoxesLayout,1,1,4,1)
        self.SetupPanelLayout.addWidget(self.SignatureCanvas,1,2,graphRowSpan,graphColSpan)
        self.SetupPanelLayout.addWidget(self.setupFileWdgt,5,2,graphRowSpan,graphColSpan)
                
        # Data panel .......................................................
        # The plots will be shown here together with the threshold interface 
        # for peak assignation. Older data can be loaded here for comparison.        
        # .................................................................

        self.DataPanel = QWidget(self)
        self.DataPanelLayout = QGridLayout()
        self.DataPanel.setLayout(self.DataPanelLayout)

        self.DataControlsLayout = QGridLayout()

        self.DataPanelTitle   = QLabel("Acquired data")
        self.DataPanelTitle.setStyleSheet(Aesthetics.titleBar)
        
        # Figure placeholder for data:
        self.DataCanvas = DataCanvas(self, width=5, height=4, dpi=100)

        # Data files
        self.dataFileWdgt = FileAccessWidgt('Data file', self.defaultDataPath, "Data files (*.csv *tsv *.txt)", self.selectDataFile, self.saveDataFile)

        # Threshold slider
        self.ThresholdSlider = QSlider()
        self.ThresholdSliderSteps = 100
                        
        if self.acquiredData.size>0:
            self.minPowserMeasured = min(self.acquiredData[1])
            self.maxPowserMeasured = max(self.acquiredData[1])
            
            self.ThresholdSlider.setMinimum(0)
            self.ThresholdSlider.setMaximum(self.ThresholdSliderSteps)
            self.ThresholdSlider.setSingleStep(1)

        self.ThresholdSlider.valueChanged.connect(self.thresholdChanged)
        self.ThresholdSlider.sliderMoved.connect(self.thresholdChanged)

        # "Calibrate process" ..............................................

        self.calibrationTitle = QLabel("Find device conversion factors")
        self.startCalibrationBtn = QPushButton('get \u03BB factors', self)
        self.startCalibrationBtn.setFixedSize(100, 30)
        self.displayCalibCoefs   = QLineEdit(self)
        self.displayCalibCoefs.setPlaceholderText("uncalibrated")
        self.displayCalibCoefs.setFixedWidth(150)
        self.displayCalibWvlts   = QLineEdit(self)
        self.displayCalibWvlts.setPlaceholderText("uncalibrated")
        self.displayCalibWvlts.setFixedWidth(150)

        self.wavelengthTag = QLabel("wavelengths:")
        self.correctionTag = QLabel("corrections:")

        # "Reassign" button ................................................
        self.reassignmentTitle = QLabel("Apply data signature")
        self.reassignBtn = QPushButton("Reassign", self)
        self.reassignBtn.setFixedSize(100, 30)

        self.startCalibrationBtn.clicked.connect(self.openCalibrationWindow)
        self.reassignBtn.clicked.connect(self.reassignData)

        # Dynamic reassignment .....................................        
        self.dynReasChk = QCheckBox("reassign dynamically")
        if self.dynReassignment == True:
            self.dynReasChk.setChecked(True)
        else:
            self.dynReasChk.setChecked(False)

        self.dynReasChk.stateChanged.connect(self.toggleDynamicReassignment)

        # Dynamic calibration .....................................        
        self.dynCalChk = QCheckBox("apply corrections")
        if self.dynCorrection == True:
            self.dynCalChk.setChecked(True)
        else:
            self.dynCalChk.setChecked(False)

        self.dynCalChk.stateChanged.connect(self.toggleDynamicCorrection)

        self.toggleCheckEnable(self.dynCalChk)

        # All elements into panel
        dataplotSpanV = 1
        dataplotSpanH = 2
        
        self.DataControlsLayout.addWidget(self.reassignmentTitle, 0,0,1,2)
        self.DataControlsLayout.addWidget(self.reassignBtn,1,0)
        self.DataControlsLayout.addWidget(self.dynReasChk,1,1)

        self.DataControlsLayout.addWidget(self.calibrationTitle, 2,0,1,2)
        self.DataControlsLayout.addWidget(self.startCalibrationBtn,3,0)
        self.DataControlsLayout.addWidget(self.dynCalChk,3,1)

        self.DataControlsLayout.addWidget(self.wavelengthTag, 4,0)
        self.DataControlsLayout.addWidget(self.displayCalibWvlts,4,1)
        self.DataControlsLayout.addWidget(self.correctionTag,5,0)                
        self.DataControlsLayout.addWidget(self.displayCalibCoefs,5,1)
        
        titleSpanV = 2
        dataplotSpanH = 3
        dataplotSpanV = 2
        self.DataPanelLayout.addWidget(self.DataPanelTitle, 0,0, titleSpanH, titleSpanV)
        self.DataPanelLayout.addLayout(self.DataControlsLayout,1,0)        
        self.DataPanelLayout.addWidget(self.ThresholdSlider,0,4, dataplotSpanV , 1)
        self.DataPanelLayout.addWidget(self.DataCanvas,0,1,dataplotSpanV,dataplotSpanH)
        self.DataPanelLayout.addWidget(self.dataFileWdgt,2,1,dataplotSpanV,dataplotSpanH)

        self.DataCanvas.draw()        
        
        # Execution panel .................................................
        self.ExecPanelTitle   = QLabel("Get data")
        self.ExecPanelTitle.setStyleSheet(Aesthetics.titleBar)        

        self.ExecPanel = QWidget(self)
        self.ExecPanelLayout = QGridLayout()
        self.ExecPanel.setLayout(self.ExecPanelLayout)

        # Reference wavelength setelctor
        wlChoices = []
        for wavelength in self.wavelengths:
            wlChoices.append(str(wavelength))
        self.refWavelthInput = ListSelect('Reference Wavelength [nm]', self.wavelengths, wlChoices, self.checkConsistency)
        self.refWavelthInput.layout.setSpacing(20)                

        # "Start button" ..................................................
        self.StartButton = QPushButton("Acquire now", self)
        self.StartButton.setFixedSize(100, 30)
                
        # Add elements to the panel
        self.ExecPanelLayout.addWidget(self.ExecPanelTitle,0,0, titleSpanH, titleSpanV)
        self.ExecPanelLayout.addWidget(self.refWavelthInput, 0,2)
        self.ExecPanelLayout.addWidget(self.StartButton,0,4)

        self.StartButton.clicked.connect(self.startStop)

        # Central widget ..................................................
        # All window panels will be nested underneath
        # .................................................................

        self.central_widget = QWidget(self)        
        
        
        # Layout 
        self.central_layout  = QGridLayout()
        self.central_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.central_widget)   
        for currPanel in [self.SetupPanel, self.DataPanel, self.ExecPanel]:
            currPanel.setStyleSheet(Aesthetics.panels)

        self.central_layout.addWidget(self.SetupPanel,0,0)
        self.central_layout.addWidget(self.DataPanel, 1,0)
        self.central_layout.addWidget(self.ExecPanel, 2,0)

    def checkConsistency(self):
        if self.wavelengths == self.calibratedWavelengths:
            print('Calibration wavelengths match the ones listed for measurement.')
            self.calibrationConsistency = True            
        else:
            print('Consistency check failed. Please check the wavelength lists.')
            self.calibrationConsistency = False
            

    def toggleCheckEnable(self, box):        
        if box.isEnabled():
            box.setEnabled(False)
            #box.setStyleSheet("color: #A9A9A9")
        else:
            box.setEnabled(True)
            #box.setStyleSheet("color: #2F2F2F")

    def selectorEnable(self, combo, message):
        combo.listDisplay.setEnabled(True)
        combo.titleWdgt.setText(message)

    def selectorDisable(self, combo, message):
        combo.listDisplay.setEnabled(False)
        combo.titleWdgt.setText(message)

    # Some widgets are enabled only when necessary conditions are met

    def buttonEnable(self, button, message):
        # Enabling the button
        button.setEnabled(True)
        button.setToolTip(message)
        #button.setStyleSheet(Aesthetics.buttons)

    def buttonDisable(self, button, message):
        # Disabling the button:        
        button.setEnabled(False)
        button.setToolTip(message)
        #button.setStyleSheet(Aesthetics.buttonsDisabled)

    def toggleButtonEnable(self, button, message):
        if button.isEnabled():
            # Disabling the button:        
            button.setEnabled(False)
            button.setToolTip(message)
            #button.setStyleSheet(Aesthetics.buttonsDisabled)
        else:
            # Enabling the button
            button.setEnabled(True)
            button.setToolTip(message)
            #button.setStyleSheet(Aesthetics.buttons)

    def toggleDynamicCorrection(self):
        self.checkConsistency()
        if self.dynCalChk.isChecked():
            if self.device.isCalibrated and self.calibrationConsistency:
                self.dynCorrection = True
                self.selectorDisable(self.refWavelthInput, "Fixed by calibration")
                self.buttonEnable(self.StartButton, "Acquisition with correction")
            else:
                self.buttonDisable(self.StartButton, "Inconsistent calibration")
        else:
            if self.device.isCalibrated:
                self.dynCorrection = False
                self.selectorEnable(self.refWavelthInput, "Reference Wavelength [nm]")
                self.buttonEnable(self.StartButton, "Acquisition without correction")

        print('dynamic correction set to ' + str(self.dynCorrection))

    def toggleDynamicReassignment(self):
        if self.dynReasChk.isChecked():
            #self.reassignData()
            self.thresholdChanged(self.data.threshold)
            self.dynReassignment = True
        else:
            self.dynReassignment = False
        print('dynamic reassignment set to ' + str(self.dynReassignment))
    
    def onCalibrationAvailable(self, table):        
        self.calibrationTable = table
        self.calibratedWavelengths = self.CalibrationWindow.calibrationWavelengths
        self.displayCalibWvlts.setText(str(self.CalibrationWindow.calibrationWavelengths))

        CorrectionStr = ""
        for factor in self.calibrationTable:
            CorrectionStr = CorrectionStr + str(round(factor,4))+","
        self.displayCalibCoefs.setText("["+CorrectionStr[:-1]+"]")
        
        if len(self.device.calibrationTable) == len(self.wavelengths):
            if self.device.isCalibrated == True:
                self.enableCalibratedAcquisition()
                try:
                    self.CalibrationWindow.close()
                except:
                    print("Window already closed")

        self.selectorDisable(self.refWavelthInput, "Fixed by calibration")

    def runCalibration(self):

        self.device.calibrationReady.connect(self.onCalibrationAvailable)

        print('passing ',self.CalibrationWindow.setWavelength)
        
        self.device.progressBarHdl = self.CalibrationWindow.progressBar
        
        if self.testMode == True:
            self.device.runCalibrationLoop(
                self.CalibrationWindow.calibrationWavelengths, 
                self.CalibrationWindow.setWavelength,'test')
        else:
            self.device.runCalibrationLoop(
                self.CalibrationWindow.calibrationWavelengths, 
                self.CalibrationWindow.setWavelength,'system')
        
        print('Calibration factors, main function: ', str(self.calibrationTable))
        print('Calibration wavelengths, main function: ', str(self.calibratedWavelengths))

    def enableCalibratedAcquisition(self):        

        self.toggleCheckEnable(self.dynCalChk)
        print('self.referenceWavelth: ' + str(self.device.referenceWavelength))
        self.refWavelthInput.listDisplay.setCurrentText(str(self.device.referenceWavelength))
        self.refWavelthInput.titleWdgt.setText("Central wavelength [nm]")
        

    def assignCurrPoint(self, currElementInd, currPulse, indL, indP, currentPower):
        
        # print("threshod being applied", self.data.threshold)
        if currentPower <= self.data.threshold:
            currentPower = 0
        else:
            if (currElementInd > 0) and (np.all(self.reassignedData[currElementInd,:] == 0)) :
                # A new pulse starts
                currPulse = currPulse + 1
                if currPulse == 0:
                    indL = 0
                    indP = 0
                elif currPulse > 0:
                    if self.order == 'PL':
                        if indL < self.signature.wavelengthCount-1:
                            indL = indL+1
                        else:
                            indL = 0
                            if indP < self.signature.powerSettingCount-1:
                                indP = indP+1
                            else:
                                indP = 0
                    elif self.order == 'LP':
                        if indP < self.signature.powerSettingCount-1:
                            indP = indP+1
                        else:
                            indP = 0
                            if indL < self.signature.wavelengthCount-1:
                                indL = indL+1                            
                            else:
                                indL = 0

        if(self.dynCorrection and self.calibrationConsistency):
            currentPower = currentPower * self.calibrationTable[indL]

        currElementInd = currElementInd+1        
        self.structuredData[currElementInd,indL,indP] = currentPower
        self.reassignedData[currElementInd,indL] = currentPower        
        self.pointers[currElementInd, :] = [indL,indP]

        print('pulse: ', currPulse, 
                'wavelength: ', self.wavelengths[indL], 
                'set power: ',self.setPowers[indP],
                '-> data[' + str(indL)+ ',' + str(indP) + ']' )


        return currElementInd, currPulse, indL, indP

    def reassignData(self):
                        
        print("Applying signature: ", self.signature.signatureString)

        if any(self.data.measuredPower):
            self.tmpData = self.data
            
            self.tmpData.wavelengthArray = np.zeros(len(self.data.measuredPower))
            self.tmpData.powerSettingArray = np.zeros(len(self.data.measuredPower))

            print('applying threshold: ', self.tmpData.threshold)
            self.tmpData.applyThreshold()
            self.tmpData.setSignature(self.signature.signatureString)
            self.tmpData.parseSignature()

            print('Field labels: ',self.tmpData.fieldLabels)
            print('Field element count: ',self.tmpData.fieldElemCount)

            peakInd  = -1 # The first peak will be at 0

            self.tmpData.wavelengthCount   = self.tmpData.fieldElemCount[self.tmpData.fieldLabels.index('L')]
            self.tmpData.powerSettingCount = self.tmpData.fieldElemCount[self.tmpData.fieldLabels.index('P')]

            # # Once the data map is ready we can replot the data 
            # # The new data structure has as many elements per row as measurements
            self.structuredData = np.zeros((len(self.tmpData.measuredPower), self.tmpData.wavelengthCount,  self.tmpData.powerSettingCount))
            self.reassignedData = np.zeros((len(self.tmpData.measuredPower), self.tmpData.wavelengthCount))
                        
            indL = 0
            indP = 0
            print('self.data.measuredPowerd inside triggerSignature... ',self.tmpData)
            for point in range(len(self.data.measuredPower)):

                if self.tmpData.measuredPower[point] > 0:
                    # After thresholding the values outside peaks are zero
                    if (point == 0 ) or (self.tmpData.measuredPower[point-1] == 0):

                        peakInd = peakInd + 1

                        if peakInd > 0:
                            if self.order == 'PL':
                                if indL < self.tmpData.wavelengthCount-1:
                                    indL = indL+1
                                else:
                                    indL = 0
                                    if indP < self.tmpData.powerSettingCount-1:
                                        indP = indP+1
                                    else:
                                        indP = 0                                    

                            elif self.order == 'LP':
                                if indP < self.tmpData.powerSettingCount-1:
                                    indP = indP+1
                                else:
                                    indP = 0
                                    if indL<self.tmpData.wavelengthCount-1:
                                        indL = indL+1
                                    else:
                                        indL = 0                                    
                    
                    print('pulse: ', peakInd, 'wavelength: ', self.wavelengths[indL], 'set power: ',self.setPowers[indP])                    
                    
                    if self.wavelengths == self.calibratedWavelengths:                        
                        if(self.dynCorrection):
                            print("Wavelengths are calibrated")
                            self.tmpData.measuredPower[point] = self.tmpData.measuredPower[point] * self.calibrationTable[indL]
                        
                    self.structuredData[point,indL,indP] = self.tmpData.measuredPower[point]
                    self.reassignedData[point,indL] = self.tmpData.measuredPower[point]
                    self.pointers[point, :] = [indL,indP]

                    self.tmpData.wavelengthArray[point]   = self.signature.wavelengths[indL]
                    self.tmpData.powerSettingArray[point] = self.signature.setPowers[indP]
                    self.data = self.tmpData
                    
            self.displaySortedData()
            self.dataWasReassigned = True
            if(self.dynCorrection):
                self.dataWasRecalibrated = True            
        else:
            print("Please open file or start acquisition")

    def saveSetupToFile(self,processFileName):
        fullPath = os.path.join(self.settingsFilePath,processFileName)
        print("saving process in  "+fullPath)
        print("Process:")
        if(os.path.isfile(fullPath)):
            print("file already exists. Overwriting content...")
        else:
            print("Creating settings file...")
        with open(fullPath, 'w') as newSettingsFile:
            newSettingsFile.write('Process:\n')
            for name in self.fieldNames:
                value = getattr(self, name)
                newSettingsFile.write(name+'\t'+str(value)+'\n')

    def setupFromFile(self,processFileName):
        # First flush the containers
        # Using the GUI function to empty the old data
        if self.wavelengths:
            for wavelength in range(len(self.wavelengths)):
                self.wavelengthWidget.deleteButton.click()            
        if self.setPowers:
            for setPower in range(len(self.setPowers)):
                self.powerSettingWidget.deleteButton.click()
            
        # Get the new values from the file
        fullPath = os.path.join(self.settingsFilePath,processFileName)
        self.parameterValues = TSVAccess.fieldValuesFromTSV(self.fieldNames, fullPath)

        for name, value in zip(self.fieldNames, self.parameterValues):
            print(name, value)
            setattr(self, name, value)

        self.orderSettingWidget.listDisplay.setCurrentIndex(self.orderSettingWidget.choices.index(self.order))
        self.durationInput.inputEdit.setText(str(self.duration))
        self.measurementIntervalInput.inputEdit.setText(str(self.measurementInterval))
        self.readoutIntervalInput.inputEdit.setText(str(self.readoutInterval))
        self.signaturePauseInput.inputEdit.setText(str(self.signaturePause))
        
        print('Adding wavelengths:')
        for wavelength in self.wavelengths:
            self.wavelengthWidget.inputBox.setText(str(wavelength))
            self.wavelengthWidget.addElement()

        print('Adding set powers:')
        for setPower in self.setPowers:
            self.powerSettingWidget.inputBox.setText(str(setPower))
            self.powerSettingWidget.addElement()
        
        self.setupFileWdgt.filePathDisplay.setText(fullPath)

    def openCalibrationWindow(self):
        self.CalibrationWindow  = CalibrationWindow(self.testMode, self.wavelengths, self.runCalibration)
        self.CalibrationWindow.show()
    
    def returnValues(self,values):
                
        timePointStr = values[0][:]
        self.realTimePowers = values[1][:] 
        
        self.selectDataStream(timePointStr)
    
    def startStop(self):
        if self.acquiringNow:                        
            self.manager.finishThreads()
            self.StartButton.setText("Aquire now")
            self.acquiringNow = False
        else:
            self.StartButton.setText("stop")
            self.acquiringNow = True
            self.acquireLPM()

    def acquireLPM(self):
        
        # For real-time reassignment
        self.realTimeLInd = 0
        self.realTimePind = 0
        self.realTimePulse = -1
        self.realTimePoint = 0
        self.timePoints = []
        
        self.acqEventLoop = QEventLoop()
        def acquisitionComplete():
            self.acqEventLoop.quit()

        basefilename =  datetime.now().strftime("%Y%m%d-%H%M_")
        
        self.manager = MeasurementManager(self.device.sensor, self.returnValues)
        # use the values from the GUI
        
        # Use the apropriate calibration reference wavelength:
        currSetWavelength = self.refWavelthInput.getCurrentSelection()
        currSetPower = self.powerSettingWidget.getCurrentSelection()
        self.manager.finished.connect(acquisitionComplete)

        if self.testMode == True:
            runningMode = 'test-standard'
        else:
            runningMode = 'system-standard'
        self.dataFileName = basefilename+'-blindMode.csv'
        self.avgTime_sec = self.readoutInterval
        self.manager.add_measurement(currSetWavelength, currSetPower, self.dataFileName, self.duration, self.avgTime_sec, runningMode)
        self.manager.start_measurements()
        self.acqEventLoop.exec()
        
        # This saves the raw data into a buffer to allow offline reassignment
        self.data.measuredPower = self.acquiredData[1]
        self.acquiringNow = False

    def convertToSeconds(self,timestampArray):       
        secArray = []

        for element in timestampArray:

            formatStr = "%Y-%m-%d %H:%M:%S.%f"                
            dt = datetime.strptime(element, formatStr)
        
            # Calculate total seconds since the start of the day
            totalSeconds = (
                dt.hour * 3600 +
                dt.minute * 60 +
                dt.second +
                dt.microsecond / 1_000_000  # Convert microseconds to seconds
            )
            secArray.append(totalSeconds)

        return secArray

    def saveDataFile(self, path):
        # Reserved for the re-assigned data, appending the original file name with
        # _reassigned. There will be one file per wavelength
                        
        savePath, baseName = os.path.split(path[:-4])
        
        if self.data.getFile() == []:
            # No file open, get the file from the stream        
            inputFullPath = self.manager.returnFileNames()[-1]            
        else: 
            autosavedFile = self.data.getFile()        
            inputFullPath = os.path.join(path,autosavedFile)
                
        outputPathsFilteredData = []
        
        # Save the originalData
        filename0 = baseName + datetime.now().strftime("%Y%m%d-%H%M_")
        filename1 = filename0 + 'raw.csv'
        outputPathFullData = os.path.join(savePath,filename1)
        print(outputPathFullData)

        if self.dataWasReassigned:            
            for wavelengthInd in range(len(self.signature.wavelengths)):
                filename2 = filename0 + str(self.signature.wavelengths[wavelengthInd]) + 'nm'
                if self.dataWasRecalibrated:
                    filename2 = filename2 + '_Corr-' + \
                    str(round(self.calibrationTable[wavelengthInd],4))

                filename2 = filename2 + '.csv'
                outputPathsFilteredData.append(os.path.join(savePath,filename2))
                                 
        header_written = {file: False for file in outputPathsFilteredData}
        with open(inputFullPath, 'r', newline='') as infile, open(outputPathFullData, 'w+', newline='') as outfileMain:
            reader = csv.reader(infile, delimiter='\t')
            writer1 = csv.writer(outfileMain, delimiter='\t')
            
            # Assuming the first row is the header
            header = next(reader)
            writer1.writerow(header)
            
            for row_index, row in enumerate(reader, start=1):             
                writer1.writerow(row)

                # For the file split:
                element = row_index - 1
                wavelengthInd = self.pointers[element, 0]
                powerInd      = self.pointers[element, 1]
                
                if not np.isnan(wavelengthInd) and not np.isnan(powerInd):
                    wavelengthInd = int(wavelengthInd)
                    powerInd = int(powerInd)
                    
                    file = outputPathsFilteredData[wavelengthInd]
                    with open(file, 'a+', newline='') as outfileFiltered:
                        writer2 = csv.writer(outfileFiltered, delimiter='\t')
                        if not header_written[file]:
                            # Write the header to this file only once
                            writer2.writerow(header)
                            header_written[file] = True
                        else:
                            row[1] = str(self.signature.wavelengths[wavelengthInd])
                            row[2] = str(self.signature.setPowers[powerInd])
                            writer2.writerow(row)

    def selectDataStream(self, timeLabels):

        currTimePoint = np.array(self.convertToSeconds(timeLabels))[-1]
        
        if self.timePoints == []:
            self.timeZero = currTimePoint
            self.timePoints.append(0)
        else:
            self.timePoints.append(currTimePoint - self.timeZero)

        if (self.dynReassignment and self.acquiringNow):

            nextElement, self.realTimePulse, self.realTimeLInd, self.realTimePind = \
                self.assignCurrPoint(self.realTimePoint, self.realTimePulse, 
                                     self.realTimeLInd, self.realTimePind, self.realTimePowers[-1])
            if self.realTimePulse >= 0:
                # Wavelength and power indices only make sense when pulses start (self.realTimePulse >=0)
                self.structuredData[self.realTimePoint,self.realTimeLInd,self.realTimePind] = \
                    self.realTimePowers[self.realTimePoint]
                self.reassignedData[self.realTimePoint,self.realTimeLInd] = self.realTimePowers[self.realTimePoint]
            self.realTimePoint = nextElement
        else:
            self.realTimePoint = self.realTimePoint + 1

        self.acquiredData = np.array([self.timePoints, self.realTimePowers])

        # Recalculate the limits for the threshold range
        if self.realTimePowers:
            self.dataLength = len(self.realTimePowers)
            
            self.minPowserMeasured = min(self.realTimePowers)
            self.maxPowserMeasured = max(self.realTimePowers)                

            self.DataCanvas.axes.set_ylim(self.minPowserMeasured, self.maxPowserMeasured)

            self.ThresholdSliderStep = (self.maxPowserMeasured - self.minPowserMeasured) / self.ThresholdSliderSteps            
            self.ThresholdSlider.setMinimum(0)
            self.ThresholdSlider.setMaximum(self.ThresholdSliderSteps)
            self.ThresholdSlider.setSingleStep(self.ThresholdSliderSteps)
            self.thresholdLine = np.ones(self.dataLength)*self.setOffset

            
            if self.maxPowserMeasured != self.minPowserMeasured:
                self.ThresholdSlider.setValue(100 * (self.data.threshold - self.minPowserMeasured)/ 
                    (self.maxPowserMeasured - self.minPowserMeasured)
                    )
            else:
                self.ThresholdSlider.setValue(0)

        if (self.dynReassignment):            
            self.displaySortedDataRealTime()
 
        else:    
            self.DataCanvas.redraw(
                    self.acquiredData[0],
                    [self.acquiredData[1],self.thresholdLine]
                )

    def selectDataFile(self, dataFile):
        
        print(dataFile)
        self.data.setFile(dataFile)
        self.data.loadDataByTag() # This already creates a data map based on the tags on the file

        timePoints = np.array(self.convertToSeconds(self.data.timeStamp))
        timePoints = timePoints - timePoints[0]
        self.acquiredData = np.array([timePoints,self.data.measuredPower])

        if self.data.measuredPower:
            self.dataLength = len(self.data.measuredPower)
            self.minPowserMeasured = min(self.data.measuredPower)
            self.maxPowserMeasured = max(self.data.measuredPower)
            self.ThresholdSliderStep = (self.maxPowserMeasured - self.minPowserMeasured) / self.ThresholdSliderSteps
            self.ThresholdSlider.setMinimum(0)
            self.ThresholdSlider.setMaximum(self.ThresholdSliderSteps)
            self.ThresholdSlider.setSingleStep(self.ThresholdSliderSteps)   
            self.displayMeasData(self.offset) # Initially 0

    def updateDurationAndReplot(self):
        self.duration = self.durationInput.value
        if not self.duration == 0:
            self.updateSignature()
            
    def updateReadoutIntervalAndReplot(self):
        self.readoutInterval = self.readoutIntervalInput.value
        self.sampleRate = self.readoutInterval
        self.updateSignature()
        
    def updateSignaturePauseAndReplot(self):
        self.signaturePause = self.signaturePauseInput.value        
        self.updateSignature()
        
    def updateAcquisitionRateAndReplot(self):
        self.measurementInterval = self.measurementIntervalInput.value
        self.updateSignature()
        
    def updateOrderAndReplot(self):
        self.order = self.orderSettingWidget.currChoice
        self.updateSignature()
        
    def updateWavelengthsAndReplot(self):
        self.wavelengths = self.wavelengthWidget.list
        print(self.wavelengths)
        self.updateSignature()
        # Update the list of wavelengths of choice for acquiring
        # During initialization of some objects this selector 
        # might not be created yet
        if hasattr(self, 'refWavelthInput'):
            self.refWavelthInput.updateList(self.wavelengths)

        
    def updatePowersAndReplot(self):
        self.setPowers = self.powerSettingWidget.list
        print(self.setPowers)
        self.updateSignature()
    
    def thresholdChanged(self,thresholdInput):
        
        if len(self.data.measuredPower) != 0 or self.acquiringNow:
            self.minPowserMeasured = min(self.acquiredData[1,:]) 
            self.maxPowserMeasured = max(self.acquiredData[1,:]) 
        else:
            self.minPowserMeasured = 0
            self.maxPowserMeasured = 1
               
        threshold = (thresholdInput/100)*(self.maxPowserMeasured - self.minPowserMeasured) + self.minPowserMeasured        
        self.data.setThreshold(threshold)
        
        if self.dynReassignment and self.acquiringNow:
            
            self.structuredData = np.zeros((self.signature.readoutCount, self.signature.wavelengthCount, self.signature.powerSettingCount))
            self.reassignedData = np.zeros((self.signature.readoutCount, self.signature.wavelengthCount))
            self.pointers = np.full((self.signature.readoutCount, 2),np.nan)
            
            reasPulseInd = -1
            reasWlthInd  = 0
            reasPrwsInd  = 0

            for element in range(len(self.realTimePowers)):
                nextElement, reasPulseInd, reasWlthInd, reasPrwsInd = \
                    self.assignCurrPoint(
                        element, reasPulseInd, reasWlthInd, reasPrwsInd, 
                        self.realTimePowers[element])
                if reasPulseInd >= 0:
                    # Wavelength and power set indices only make sense from the first pulse (reasPuldeInd >=0)
                    self.structuredData[element,reasWlthInd,reasPrwsInd] = \
                        self.realTimePowers[element]
                    self.reassignedData[element,reasWlthInd] = self.realTimePowers[element]
                nextElement = element

            self.realTimePoint = element
            self.realTimePulse = reasPulseInd
            self.realTimeLInd  = reasWlthInd 
            self.realTimePind  = reasPrwsInd
                    
            # self.displaySortedData()

        elif len(self.data.measuredPower) != 0 or len(self.realTimePowers) != 0:
                self.displayMeasData(self.data.threshold)

    def displayMeasData(self,value):        
        self.setOffset = value
        print('displayMeasData -> displayMeasData(self,value), with value:',self.setOffset)
        self.thresholdLine = np.ones(self.dataLength)*self.data.threshold
        self.DataCanvas.redraw(
            self.acquiredData[0],
            [self.acquiredData[1],self.thresholdLine]
        )

    def displaySortedData(self):
        RGB = np.zeros((self.signature.wavelengthCount,3))
        RGB[:,0] = self.signature.Red
        RGB[:,1] = self.signature.Green
        RGB[:,2] = self.signature.Blue

        self.thresholdLine = np.ones(self.dataLength)*self.setOffset
        print('displaySortedData -> displayMeasData(self), with self.setOffset:',self.setOffset)
        self.DataCanvas.axes.clear()
        self.DataCanvas.axes.plot(self.acquiredData[0],self.thresholdLine, color = 'gray', linestyle='dashed')
        self.DataCanvas.draw()
        for wavelength in range(self.data.wavelengthCount):
            plotColor = (RGB[wavelength,0]/255,RGB[wavelength,1]/255,RGB[wavelength,2]/255)  
            
            self.DataCanvas.drawOnTop(
                self.acquiredData[0],
                [self.reassignedData[:,wavelength]], 
                plotColor
            )

    def displaySortedDataRealTime(self):
       
        RGB = np.zeros((len(self.wavelengths),3))
        
        RGB[:,0] = self.signature.Red
        RGB[:,1] = self.signature.Green
        RGB[:,2] = self.signature.Blue
        
        for wavelength in range(self.signature.wavelengthCount):
            plotColor = (RGB[wavelength,0]/255,RGB[wavelength,1]/255,RGB[wavelength,2]/255)  

            self.DataCanvas.drawOnTop(
                self.timePoints,
                [self.reassignedData[0:len(self.timePoints),wavelength]],
                plotColor
            )
        self.DataCanvas.axes.plot(self.timePoints,self.thresholdLine,color='gray', linestyle='dashed')
        self.DataCanvas.draw()
            
    def updateSignature(self):
        self.signature.setParameters(
            self.wavelengths, self.setPowers, 
            self.measurementInterval, self.readoutInterval, 
            self.duration, self.signaturePause, self.order
            )
        ###########################################################
        # print('wavelengths: ', self.wavelengths, 
        #       'set powers: ', self.setPowers, 
        #       'measurement Interval: ', self.measurementInterval, 
        #       'sample rate: ', self.readoutInterval, 
        #       'duration: ', self.duration, 
        #       'pauses of: ', self.signaturePause, 
        #       "order of acquisition: ", self.order)
        ############################################################
        if not (self.wavelengths == [] or self.wavelengths == [0]) and \
            not (self.setPowers == [] or self.setPowers == [0] ) and \
            not (self.duration == 0 or self.readoutInterval == 0) and \
            not self.order == "":
            
            self.signature.calculateSignature()
            self.sigProfile = self.signature.signature
            
            wavelengthCount = len(self.wavelengths)
            
            if wavelengthCount > 0:
                RGB = np.zeros((wavelengthCount,3))
                RGB[:,0] = self.signature.Red
                RGB[:,1] = self.signature.Green
                RGB[:,2] = self.signature.Blue
                self.SignatureCanvas.axes.clear()
                for wavelength in range(len(self.wavelengths)):
                    plotColor = (RGB[wavelength,0]/255,RGB[wavelength,1]/255,RGB[wavelength,2]/255)
                    self.SignatureCanvas.axes.plot(self.sigProfile[wavelength], color=plotColor)
                self.SignatureCanvas.draw()
            else:
                print("Nothing to update")

            # Memory allocation for the data according to instructions
            self.structuredData = np.zeros((self.signature.readoutCount, self.signature.wavelengthCount,  self.signature.powerSettingCount))
            self.reassignedData = np.zeros((self.signature.readoutCount, self.signature.wavelengthCount))
            self.pointers = np.full((self.signature.readoutCount, 2),np.nan)

def main(mode):
    app = QApplication([])
    testMode = (mode == 'test')
    appWindow = programGUI(testMode)
    appWindow.show()
    sys.exit(app.exec())
    # Under Windows 11 the desktop themes override components
    # leading to display issues (unreadable text, etc.). Using
    # the system palette resolves this and provides integration 
    # with the rest of the applications:
    Aesthetics.Functions.apply_system_palette(app)

if __name__ == "__main__":
    mode = 'system'
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    main(mode)
