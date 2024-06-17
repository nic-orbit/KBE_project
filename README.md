# KBE_project

# Contributers

Nicolas Oidtmann

Gargi Sunil Pantoji

# Installation

Use the requirements.txt file in this repository. 

```console
conda create --name KBEvenv --file requirements.txt
```

It should be noted, that for this application to work, an installation of parapy is required, which is commercially available. 

# User Guide

To start the KBE Application, run the main.py file inside the src folder. 

The user inputs are expected mainly as inputs for the mission class and the payload class and should be entered into the application by the user. Furthermore, since the app is a configurator for a CubeSat Mission, there are multiple .csv files containing possible elements that could  be part of the cubesat mission. These include the subsystem and component libraries, thermal coating libraries and the list of possible ground stations. The user is free to extend these libraries, allowing to stay up to date with the state of the are technical developments. 

To allow the user to explore the design space further, there are three design parameters, that can be adjusted within the KBE application, which will impact the selection of the subsystems. These weights balance the importance of mass, cost and power in the design of the cubesat. 

When the root element is selected, the user has the option to generate a report summarizing the current design, together with plots which are saved in the plots subfolder. Also, the user can generate a step file of the cubesat design which can then be exported to any 3D CAD tool for further analysis. 

All libraries, generated reports, plots and step files can be found in the cubesat_configurator folder under the corresponding subfolder. 

With any further questions, feel free to reach out to the contributers stated above. 

This code base has been developed in the frame of the Knowledge Based Engineering course taught at TU Delft. 

### Create UML Classes overview

do everything from the src folder
```console
cd src
```
To generate .png files to check:
```console
pyreverse . -m y -o png
```
generate .dot files (exclude -m y if you do not want the )
```console
pyreverse . -m y
```
generate .xml files that can be imported to draw.io
```console
graphviz2drawio classes.dot
```