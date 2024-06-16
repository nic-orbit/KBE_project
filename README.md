# KBE_project

# Contributers

Nicolas Oidtmann

Gargi Sunil Pantoji

# Installation

Use the requirements.txt file in this repository. 

```console
conda create --name KBEvenv --file requirements.txt
```

# Create UML Classes overview

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