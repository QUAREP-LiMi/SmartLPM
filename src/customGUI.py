"""
Created on 
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
import numpy as np
import os
import time
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QMenuBar, QMenu, QPushButton, QDoubleSpinBox, QVBoxLayout, QHBoxLayout,
    QLabel, QGridLayout, QComboBox, QLineEdit, QGroupBox, QSpinBox, QApplication, QSlider, QFileDialog, QLayout
)
from PySide6.QtGui import QPainter, QColor, QImage, QImage, QPalette
from PIL import Image, ImageQt, ImageDraw

class Aesthetics:
    # Many of these functions and aesthetic choices are used across 
    # my other projects but under windows 11 allowing color combinations
    # from the system palette worked better at the computer tested
    # (dark theme). Uncomment the lines below for testing

    class Borders:
        style  = "solid"
        color  = "gray"
        colorDisabled = "#A9A9A9"
        width  = "1px"
        radius = "10px"
    class Colors:
        fontGeneral = "#2F2F2F"
        fontDisabled = "#A9A9A9"
        background = "#D9D9D9"
        backgroundBtn = "#E1E1E1"
        backgroundDisabled = "#F0F0F0"
        borderColor     =  "#C3C3C3"
        boxes   = "white"
        link    = "blue"
        visited = "purple"

    spinboxes = f"""
        QDoubleSpinBox{{
#            background-color: {Colors.boxes};
#            color: {Colors.fontGeneral}; 
            font-size: 16px;
        }}
        """
    monitors = f"""
        QLineEdit{{
#            background-color: {Colors.boxes}; 
#            color: {Colors.fontGeneral}; 
            padding: 0px 10px;
            border: 1px solid black;
        }}
        """
    window = f"""
        QWidget{{
#            background-color: {Colors.background};
#            color: {Colors.fontGeneral};
            border: {Colors.borderColor};
        }}
        """
    panels = f"""
        QGroupBox{{
        border-radius: {Borders.radius};
        }}
        """
    buttons = f"""
        QPushButton {{
            border-radius: {Borders.radius};
        }}
        """
    buttonsDisabled = f"""
        QPushButton {{
            border-style: {Borders.style};
            border-width: {Borders.width};
        }}
        """        
    titleBar = f"""
            QLabel {{
                font-weight: bold;
                font-size: 14pt;
            }}
        """
    verticalSlider = f"""
            QSlider::groove:vertical {{
            border: 1px solid;
            margin: 1px;
            }}
            QSlider::handle:vertical {{
            border: 1px solid;
            height: 40px;
            width: 40px;
            margin: -15px 0px;
            }}
        """
    PushPopLists = f"""
        QLineEdit {{
            padding: 0px 10px;
        }}
        """

class Functions:
    @staticmethod
    def apply_system_palette(app):
        # Get the current system palette
        palette = app.palette()
        window_background = palette.color(QPalette.Window)
        window_text = palette.color(QPalette.WindowText)

        # Determine if the theme is bright or dark based on the luminance of the background color
        # A simple condition can be applied based on RGB components to differentiate bright/dark themes
        def is_dark(color):
            r, g, b = color.red(), color.green(), color.blue()
            # Calculate luminance using the formula for perceived brightness
            return (0.299 * r + 0.587 * g + 0.114 * b) < 128

        text_color = "#FFFFFF" if is_dark(window_background) else "#000000"

        # Apply the dynamically generated stylesheet
        app.setStyleSheet(f"""
        QWidget {{
            background-color: {window_background.name()};
            color: {text_color};
        }}
        """)

class FileAccessWidgt(QWidget):
    # All file access GUIs combined
    def __init__(self, title, defaultPath, filter, effect1, effect2):
        super().__init__()

        self.defaultPath = defaultPath
        self.filter = filter
        self.pathStr = ""
        self.loadFunction = effect1
        self.saveFunction = effect2
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.titleWdgt   = QLabel(title)
        self.filePathDisplay = QLineEdit(self)
        
        self.openFileBtn = QPushButton("load", self)
        self.openFileBtn.setFixedSize(80, 30)        

        self.saveFileBtn = QPushButton("save", self)
        self.saveFileBtn.setFixedSize(80, 30)        

        self.filePathDisplay.returnPressed.connect(self.setPath)
        self.openFileBtn.clicked.connect(self.openFile)
        self.saveFileBtn.clicked.connect(self.saveFile)

        self.layout.addWidget(self.titleWdgt)
        self.layout.addWidget(self.filePathDisplay)
        self.layout.addWidget(self.openFileBtn)
        self.layout.addWidget(self.saveFileBtn)

    def saveFile(self):
        self.pathStr, _ = QFileDialog.getSaveFileName(self,"Save File",self.defaultPath,self.filter)        
        self.saveFunction(self.pathStr)
        print('saveding to'+self.pathStr)

    def openFile(self):
        self.loadFileDiag = QFileDialog(self)
        self.loadFileDiag.setDirectory(self.defaultPath)
        self.loadFileDiag.setFileMode(QFileDialog.FileMode.AnyFile)
        self.loadFileDiag.setNameFilter(self.filter)

        self.pathStr, _ = self.loadFileDiag.getOpenFileName(self,"Open file",self.defaultPath,self.filter)
        if self.pathStr:            
            self.filePathDisplay.setText(self.pathStr)
            self.loadFunction(self.pathStr)

    def setPath(self):
        self.pathStr = self.filePathDisplay.text()
        self.loadFunction(self.pathStr)

class ListSelect(QWidget):
    # GUI simplified access to a selection list and a 
    # button to run a command on the selected item
    def __init__(self, title, choices, choiceNames, effect):
        super().__init__()

        self.function = effect
        self.choices  = choices
        self.currChoice = ""
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.titleWdgt   = QLabel(title)
        self.listDisplay = QComboBox(self)
        
        for option in choiceNames:
            self.listDisplay.addItem(option)
            
        self.layout.addWidget(self.titleWdgt)
        self.layout.addWidget(self.listDisplay)

        self.listDisplay.currentIndexChanged.connect(self.updateChoice)
    
        self.setStyleSheet(Aesthetics.PushPopLists)

    def updateList(self, newlist):
        self.listDisplay.clear()
        for option in newlist:
            self.listDisplay.addItem(str(option))

    def updateChoice(self,choice):
        self.currChoice = self.choices[choice]
        self.function()
    
    def getCurrentSelection(self):
        return self.listDisplay.currentText()
        

class InputBox(QWidget):
    # Input text box connected to a function
    def __init__(self, title, units, effect):
        super().__init__()

        self.value = 0
        self.function = effect
        self.layout = QHBoxLayout()            
        self.setLayout(self.layout)
        
        self.titleLbl = QLabel(title+' ['+units+']')
        
        self.inputEdit    = QLineEdit(self)
        self.inputEdit.textChanged.connect(self.setValue)
        self.inputEdit.returnPressed.connect(self.setValue)

        self.layout.addWidget(self.titleLbl)
        self.layout.setAlignment(self.titleLbl, Qt.AlignRight)
        self.layout.addWidget(self.inputEdit)
        self.layout.setAlignment(self.inputEdit, Qt.AlignLeft)

        self.setFixedHeight(40)

    def setValue(self):
        inputText = self.inputEdit.text()
        try:
            self.value = int(inputText)
            self.function()
        except ValueError:
            print("Invalid input: Please enter an integer.")

class PushPopList(QWidget):
    # GUI for adding removing and selecting elements 
    # from a stack
    def __init__(self, title, units, effect):
        super().__init__()

        self.function = effect
        self.list = []

        self.titleLbl = QLabel(title + ' [' + units + ']')            
        self.selectLbl = QLabel('select')

        # Result display
        self.showList = QLineEdit()
#        self.showList.setStyleSheet(Aesthetics.monitors)
        
        self.showList.setPlaceholderText('[]')
        self.showList.setReadOnly(True)

        # Create ComboBox to display items
        self.combo_box = QComboBox(self)

        # Create 'Delete' button to remove selected item
        self.deleteButton = QPushButton("remove", self)
        self.deleteButton.clicked.connect(self.removeElement)

        # To add elements
        self.inputBox = QLineEdit(self)
        self.inputBox.returnPressed.connect(self.addElement)
        self.inputBox.setPlaceholderText('input')
#        self.inputBox.setStyleSheet(Aesthetics.monitors)

        # Create 'Push' button to add items
        self.addButton = QPushButton("add", self)
        self.addButton.clicked.connect(self.addElement)

        # Layout for easy-esthetic buttons alignment
        self.layout = QGridLayout()
        titlerowSpan = 1
        titlecolSpan = 2
        self.layout.addWidget(self.titleLbl, 0,0, titlerowSpan, titlecolSpan)
        rowSpan = 1
        colSpan = 3
        self.layout.addWidget(self.showList,0,2, rowSpan, colSpan)
        self.layout.addWidget(self.selectLbl,1,0)
        self.layout.addWidget(self.combo_box,1,1)
        self.layout.addWidget(self.deleteButton,1,2)
        self.layout.addWidget(self.inputBox,1,3)
        self.layout.addWidget(self.addButton,1,4)
        
        #self.layout.setSpacing(10)

        self.deleteButton.setEnabled(False)

        # Connect signal to handle item selection to enable/disable delete button
        self.combo_box.currentIndexChanged.connect(self.updateDeleteButtonState)

        # Set the layout
        self.setLayout(self.layout)
        self.setFixedHeight(80)

    def addElement(self):        
        text = self.inputBox.text().strip()
        if text:
            self.combo_box.addItem(text)
            self.inputBox.clear()
            try:
                self.list.append(int(text))
            except ValueError:
                print("Please provide an integer")

            displayString = '['+','.join(str(element) for element in self.list)+']'
            self.showList.setText(displayString)
            self.function()

    def getCurrentSelection(self):
        idx = self.combo_box.currentIndex()
        return self.list[idx]

    def removeElement(self):
        idx = self.combo_box.currentIndex()
        if idx != -1:
            self.combo_box.removeItem(idx)

            self.list.pop(idx)
            displayString = '['+','.join(str(element) for element in self.list)+']'
            self.showList.setText(displayString)
            self.function()

    def updateDeleteButtonState(self):
        self.deleteButton.setEnabled(self.combo_box.currentIndex() != -1)
