# LION Archive

*******************************

Every quarter it is required to distribute the latest LION and District files from Production to Archive SDEs, as well as to modify associated layers. This script distributes LION and district files across the necessary directories within DCP’s file structure.

### Prerequisites

A version of Python with the default ArcPy installation that comes with ArcGIS Desktop is required in order to utilize Metadata functionality that is currently not available in the default ArcPy installation that comes with ArcGIS Pro (Python 3). 

##### LION_Prod2Archive2MDrive.py

```
arcpy, os, re, traceback, sys, datetime, ConfigParser
```

### Instructions for running

##### LION_Prod2Archive2MDrive.py

1. Open the script in any integrated development environment (PyCharm is suggested)

2. Ensure that your IDE is set to be utilizing the default version of Python 2 that comes with ArcGIS as its interpreter for this script. This particular python distribution is required for its metadata functionality

3. Ensure that all paths listed in configuration file are still valid

3. Run the script, the script will distribute LION Production files to the Archive SDE and re-source LION / District layer files on the M drive.


