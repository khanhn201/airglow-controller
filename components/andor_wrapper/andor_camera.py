
from .andorsdk_wrapper import andorsdk
import logging
import sys
import os
sys.path.append

# This import only works if andor_camera.py is imported from outside components (see main_scheduler.py for import)
# Will not work if import inside components


class AndorCamera:

    def __init__(self):
        re = andorsdk.initialize()
        logging.info("CCD init: " + str(re))
        logging.info('Initialized CCD')
        print(re)

    def getTemperature(self):
        re = andorsdk.getTemperature()
        print(re[0])
        logging.debug("CCD get temp: " + str(re[0]) + " " + str(re[1]))
        return re[1]

    def getTemperatureRange(self):
        re = andorsdk.getTemperatureRange()
        print(re[0])
        return (re[1], re[2])

    def setTemperature(self, t):
        re = andorsdk.setTemperature(t)
        logging.debug("CCD set temp: " + str(re))
        print(re)

    def turnOffCooler(self):
        re = andorsdk.turnOffCooler()
        logging.debug("CCD turn off cooler: " + str(re))
        print(re)

    def turnOnCooler(self):
        re = andorsdk.turnOnCooler()
        logging.debug("CCD turn on cooler: " + str(re))
        print(re)

    def shutDown(self):
        re = andorsdk.shutDown()
        logging.info("CCD shutdown: " + str(re))
        print(re)

    def setReadMode(self, mode=4):
        """Set the read mode

        Parameter
        -------
        mode: 4 for image mode
        """
        re = andorsdk.setReadMode(mode)
        logging.debug("CCD set read mode: " + str(re))
        print(re)

    def setExposureTime(self, time):
        re = andorsdk.setExposureTime(time)
        logging.debug("CCD set exp: " + str(re))
        print(re)

    def setShutter(self, typ=0, mode=0, closingtime=0, openingtime=0):
        re = andorsdk.setShutter(typ, mode, closingtime, openingtime)
        logging.debug("CCD set shutter: " + str(re))
        print(re)

    def setAcquisitionMode(self, mode=1):
        re = andorsdk.setAcquisitionMode(mode)
        logging.debug("CCD set acquisition mode: " + str(re))
        print(re)

    def setImage(self, hbin=2, vbin=2, hstart=1, hend=1024, vstart=1, vend=1024):
        self.hbin = hbin
        self.vbin = vbin
        self.hstart = hstart
        self.hend = hend
        self.vstart = vstart
        self.vend = vend
        re = andorsdk.setImage(hbin, vbin, hstart, hend, vstart, vend)
        logging.debug("CCD set image: " + str(re))
        print(re)

    def startAcquisition(self):
        re = andorsdk.startAcquisition()
        logging.debug("CCD start acquisition: " + str(re))
        print(re)

    def getStatus(self):
        """Get the current status
        """
        re = andorsdk.getStatus()
        logging.debug("CCD status: " + str(re[0]) + " " + str(re[1]))
        print(re[0])
        return re[1]

    def getImage(self):
        """Get the most recent image

        Returns
        -------
        img
            a np 2d array
        """

        re = andorsdk.getImage(self.hbin, self.vbin,
                               self.hstart, self.hend, self.vstart, self.vend)
        logging.debug("CCD get image: " + str(re[0]))
        print(re[0])

        return re[1]

    def setShiftSpeed(self, indexH=2, indexV=2, preAmpGain=2, ttype=0):
        re = andorsdk.setHSSpeed(indexH, ttype)
        logging.debug("CCD set horizontal shift speed: " + str(re))
        re = andorsdk.setVSSpeed(indexV)
        logging.debug("CCD set vertical shift speed: " + str(re))
        re = andorsdk.setPreAmpGain(preAmpGain)
        logging.debug("CCD set preamp gain: " + str(re))

