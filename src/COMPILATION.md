To create an exe file we used pyinstaller

In a conda terminal, after activating the environment, 
*pip install pyinstaller*

Executed from a folder above *pyinstaller src\SmartLPM.exe* creates a *dist* folder with the executable and an *_internal* folder. In this folder all the dependencies will be copied. Compiledin this way the executable will be as fast as it an be.
