# SmartLPM



## Introduction

Smart Light Power Measurement (SmartLPM) is a tool for acquiring and sorting light power data automatically. What makes it different from other applications is its ability to classify the incoming data according to user instructions. In order to do this it detects patterns in the illumination data matching predefined sequences. We will call these patterns the data signature of the experiment.

### The problem to resolve

The assessment of light power and stability over multiple light sources and different set powers can be time consuming and prone to introducing errors. On the image below we depict illumination sequences for studying the linear response (left) and power stability over long periods of time (right) for an example with four different lasers. The first example consists in 16 phases and the second, if done every 5 minutes for 2h has 96 phases. 

*The critical problem is the need reconfigure the acquisition (tuning the power meter and recording the set power) before each phase.*
![MainWin](doc/smartLPM-09-Pulses.jpg?raw=true "Main window")
*Fig. 1. Pulse sequence for linearity (left) and stability assessment (right) test experiments. The stability test example has been cropped for illustration purposes.*

On the examples above, operating the devices manually in the first experiment would be very impractical and in the second one, where pulses are interleaved regularly over hours is not realizable. Alternatively the same experiments can be automated. Some microscope control suites provide tools to control external devices as power meters, allowing this as demonstrated by the QUAREP-LiMi community [2]. Unfortunately, in general this is not possible. 

*In general, while it is still possible in most modern microscopes to setup the illumination sequences, power meters provide no way to predict them*. Until now, unless the microscope has the ability to prepare the power meter for each individual test a human operator remains necessary. SmartLPM was programmed to circumvent this problem.

### Semi-automatic power measurement

Provided that in both cases the same information is collected and that none of them require human intervention, a fully automated power approach should start with the press of a button. We propose the semi-automatic approach as requiring the press of two buttons. One for starting the illumination and another for starting the acquisition. The system processing the data has to be able to do all the tuning and classification tasks by itself. SmartLPM provides the functionalities needed to do this:

1. **Direct measurement** of optical powers using a power meter device (currently the Thorlabs PM family [1] is supported). This function replicates the standard acquisition mode of the vendor software, here the Optical Power Monitor software from Thorlabs.
2. **Automatic data parsing** (reassignment). The data can be split into groups according to their wavelengths and set powers in an unsupervised manner. This concept is illustrated in fig. 2
3. **Predictive tuning**. There is no need to tune the power meter device manually if the wavelengths are given initially. This is the second and last requirement for running complex power measurement tests automatically. 
4. **Management of the experiment instructions**. Different experiment recipes can be created and visualized easily. These recipes can be stored and retrieved for later use.
5. **Data sorting over files**. This function is aimed to work in combination with the QUAREP-LiMi Tool Kit [2] for browsing acquisition data over time.

The data parsing can be done during the acquisition or afterwards, directly on the acquisition data stream or on the contents of a data file.

![MainWin](doc/smartLPM-00-Concept.jpg?raw=true "Main window")
*Fig. 2. Automatic data parsing. The acquired data (plot below) is compared to the experiment signature proposed (plot above) leading to the matching pairs. In this example the intensities used creating the test data set do not match the proposed ones.*
Despite being developed for microscopes this software can be used in the same way for any illumination device with selectable wavelengths and adjustable powers.


## Using SmartLPM

To setup and carry out power assessment experiments this software has two separate panels. 
Setup panel. On the top one It is possible to introduce and visualize the instructions (fig. 3):
- A list of wavelengths [nm]. New values can be introduced and removed.
- A list of power settings [%]. New values can be introduced and removed.
- Order of the experiment. Loop over all wavelengths available before the next power setting powers(wavelengths) or loop over all power settings available before the next wavelength wavelengths(powers).
- The duration of the experiments [s]. After the given time the acquisition will be terminated.
- The acquisition interval [s]. All the power/wavelength combinations will be repeated for the duration of the experiment. The acquisition interval establishes the time each of these cycles will take.
- The sample interval [s]. The rate at which the power meter collects data points. For the Thorlabs power meter currently supported this time has to be of at least 1s.
- A signature pause [s]. The software needs pauses to distinguish the different pulses. This number represents the duration of these pauses.
At the moment the duration of the pulses is not taken into account for parsing, as this is done solely by comparing to a threshold.

![MainWin](doc/smartLPM-02-Defining_experiment.jpg?raw=true "Main window")
*Fig. 3. Data signature generation. User input for the description of the pulse series that will be acquired.*
These descriptions can be saved as csv files and reloaded for later use.

Acquisition panel. Starting from the bottom right corner, next to the Acquire now button a wavelength from the list introduced above can be chosen for tuning the power meter. In this way the acquisition can be started in a conventional way. 

Reassignment (parsing). Once the acquisition starts or in case we loaded an existing data file we can set a threshold value using the slider on the right. This threshold will be used to distinguish the pulses for matching them to the data signature defined before. To do this we can press Reassign or check the reassign dynamically tick box to do it once the complete data set is available or during the acquisition. The effect of the reassignment function is shown in fig. 4.

![MainWin](doc/smartLPM-07-Acquisition.jpg?raw=true "Main window")
*Fig. 4 Acquisition panel. On the left are the controls for the data parsing and predictive tuning and on the right the acquired data is shown (here showing the effect of applying the reassignment function).*

Calibration and predictive tuning. If we plan to acquire pulses of multiple wavelengths a the acquired data has to be corrected as described in the predictive tuning section of this manual. 
A calibration process will find the appropriate corrections for each wavelength detected. The calibration process consists in the following:
On the system we are going to study we turn on the illumination source that we plan to use as a reference. As an example, a laser of 488nm. The software will run a short test on this source, tuning the power meter at each of the wavelengths listed to use later. Provided that only while tuned at the same wavelength the measured power will be correct the software will find the ratios for all the other tuning settings. The ratio for the reference wavelength will be 1. These ratios are the correction factors that will be applied later. 
The calibration process takes only 5s per wavelength and is transparent for the user, but some considerations are important.
    - During process the power meter must be illuminated at the reference wavelength during the calibration.
    - The apply corrections tick box is disabled until a calibration is available.
    - Once the system is calibrated the set wavelength for the power meter is fixed to the reference one. The selection pop-up list is disabled.
    - Calibration here refers to the finding of correction factors to avoid the manual tuning of the power meter. The power itself meter has to be calibrated and this process has nothing to do with it.

![MainWin](doc/smartLPM-06-Calibration.jpg?raw=true "Main window")
*Fig. 5 Calibration procedure*
Once the process is calibrated the corrections can be applied during the acquisition or by pressing Reassign with the apply corrections tick box enabled.


Saving the data. If the data has been parsed the save button will create one file per wavelength.

How SmartLPM works
SmartLPM is not very smart, but does some simple but effective classification. The two key ideas implemented are the automatic data parsing and predictive tuning.

Automatic data parsing
By parsing illumination pulses this software classifies and corrects the illumination powers acquired in real time. Instead of electronic signals the microscope and the power meter communicate though the same optical data being collected (fig.6). 

![MainWin](doc/smartLPM-04-Interplay.jpg?raw=true "Main window")
*Fig. 6. Real time parsing. The data from different illumination is classified according to given instructions. Each set is saved into a separate file.*

In practice the only requirement is to set the illumination as sequences of pulses and pauses. In future releases other ways of parsing data might be introduced but we found this approach very robust and relatively easy to setup in most microscopes.

## Predictive Tuning
The optical power presented by a power meter is the result of multiplying the photocurrent generated on the sensor by its spectral responsivity. Because responsivities are a function of the light wavelength setting up a power meter with the wrong value leads to incorrect power estimations. It is still possible to recover the correct value if multiply by the ratio between applicable responsitity to the applied one (fig 3). Interestingly, this the ratio coincides with the inverse ratio of optical powers. This can be used to obtain a series of correction factors in a quick way.
It is now possible to let the power meter run continuously tuned under a reference wavelength (accurate for only one of the wavelengths tested) and to automatically correct for all the other ones. The data signature has the information to choose the appropriate correction factor for each pulse. Considering the shape of the responsivity curves (figure below) we recommend to use reference wavelengths in the center of the spectral range used.

![MainWin](doc/smartLPM-05-Tuning.jpg?raw=true "Main window")
*Fig. 7 Typical responsivity curve of a power meter device and how to correct power estimations. In red we have the illumination power estimated tuning the power meter at an arbitrary wavelength and how the correct power can be retrieved.*
## Appendix I. Concepts used in this manual
SmartLPM is a tool for the measurement of highly monchromatic light sources as lasers or other devices if the light is collected after a narrow band-pass filter. A use case is the quality assessment of microscopes in general, where the performance of illumination devices impacts imaging aspects as bleaching, phototoxicity or the ability handle images intensities in a quantitative manner.

*Illumination power* is the total energy per unit time -typically in milliwatt (mW)- transported by light. Relevant illumination powers in microscopy are the output of the laser devices and the power delivered to a sample during an imaging experiment.

*Irradiance* is the illumination power per unit area either emitted, collected or traversing a surface.  - typically expressed in mW/μm2-. In microscopy it is more relevant to know this number as the signal intensities and other effects on the sample depend on it. Nevertheless, for a given light path (objective, filters, etc.) the irradiance must be proportional to the illumination power.

*Optical power meters*. Unlike spectrometers, where it is possible to know how much power an illumination device produces at every wavelength within certain range, optical power meters provide a single number, assuming that all the light collected has a given wavelength. There is no spatial information either: only the light illuminating the sensor area is detected, and its power is averaged along the response time of the device.

*Measuring optical powers in a microscopes*
To ensure the correct operation of microscopes it is necessary to measure the illumination power and stability of each light source. This can be done measuring powers over time together with the corresponding wavelengths and set powers (table below)

| timestamp				    | wavelength[nm]	| setting[%]	| power[mW]| 
| -----------               | -----------       |-----------    |----------- |
| 2024-06-27 10:32:54.713		| 488			    | 80  		| 2.84024952684| 
| 2024-06-27 10:32:55.747		| 488			    | 80		| 2.8464990042| 
| 2024-06-27 10:32:56.713		| 488			    | 80	   	| 2.84486841114| 
| 2024-06-27 10:32:57.713		| 488			    | 80	    | 2.84345842012| 
| 2024-06-27 10:32:58.715		| 488			    | 80    	| 2.84513334112| 
| 2024-06-27 10:32:59.714		| 488			    | 80 		| 2.84220336708| 
| 2024-06-27 10:33:00.713		| 488			    | 80	   	| 2.83964277532| 
| 2024-06-27 10:33:01.714		| 488			    | 80		| 2.84453576236| 
| ...                           | ...               | ...       | ...| 

## Installation
At the moment this program is provided as python source code. For controlling the power meters from Thorlaabs it requires the TLPM64.dll driver wich is distributed with the [Optical Power Monitor software](https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=4037). The driver has to be saved together with the python files. Copy all the source files together with the folders under the src folder. These folders contain auxiliary files needed by the application to run properly.

## Authors and acknowledgment
The program was originally created by Nasser Darwish, imaging expert at the Imaging and Optics Facility, Institute of Science and Technology Austria. Arne Fallisch, Staff Scientist at the Life Imaging Center, Albert-Ludwigs Universität Freiburg has contributed in multiple ways to the improvement of the software.

## License
Copyright©2025. Institute of Science and Technology Austria (ISTA). All Rights Reserved.
hich is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation in version 3.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License v3 for more details.
You should have received a copy of the GNU General Public License v3 along with this program.  If not, see https://www.gnu.org/licenses/.
Contact the Technology Transfer Office, ISTA, Am Campus 1, A-3400 Klosterneuburg, Austria, +43-(0)2243 9000, twist@ist.ac.at, for commercial licensing opportunities.

## Project status
Version 1.0 This is the first official release of SmartLPM. We will address the bugs detected according to our disponibility. 
