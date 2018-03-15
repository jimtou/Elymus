Elymus - Lightweight Bitcoin NewYork (BTC2) Client
=====================================

::
  Elymus is lightweight Bitcoin NewYork (BTC2) client. It is powered 
  by electrum 3.0.5. 
  Elymus only supports BTC2, not compatible bitcoin and electrum
  anymore. Elymus client only works with Elymus servers.

  electrum:
  Licence: MIT Licence
  Author: Thomas Voegtlin
  Language: Python
  Homepage: https://electrum.org/

Getting started
===============

Elymus is a pure python application.
You will see about 10 minutes blocker header synchronization 
from server for the first time use. From the network window, 
you know the completion of sync. 


Linux
-----

Install the Qt dependencies:: 

    sudo apt-get install python3-pyqt5

Downloaded the official package, then you can run Elymus from its 
root directory, without installing it on your system.

    ./elymus



Windows
-------

Download and install the python3 from https://www.python.org/downloads/. 
It is python3 here!!! current version is 3.6.4

Install the Qt dependencies:
open windows cmd window, go to python install directory, in my windows 10, the default 
installed directory is "C:\Users\xxxx\AppData\Local\Programs\Python\Python36-32"

    "python dir"\scripts\pip.exe install pyqt5

Downlaod the official package, the run Elymus from its directory.

    "python dir"\python.exe elymus


windows installer of Elymus client will be released later.



--End--
