import os
import sys
import logging
import signal
import scipy
import numpy as np
import pickle
from time import sleep
from datetime import datetime, timedelta
import smtplib, ssl
from config import config, skyscan_config, filterwheel_config
from schedule import observations
import ephem

import utilities.time_helper
from utilities.image_taker import Image_Helper
from utilities.send_mail import SendMail

from components.camera import getCamera
from components.shutterhid import HIDLaserShutter
#from components.sky_scanner import SkyScanner
from components.sky_scanner_keo import SkyScanner
from components.skyalert import SkyAlert
from components.powercontrol import PowerControl
from components.filterwheel import FilterWheel

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Choose what to test. Select from:
#   CCD - Andor CCD
#   SkyScanner - SkyScanner
#   FilterWheel - Filterwheel
#   Sequence - Goes through a schedule sequence to check pointing to Cardinal, Laser, and FilterWheel
#   Sun - Points the SS to the sun
#   SkyAlert - Tests cloud sensor
#   gmail - Test the gmail connection
#   LaserShutter - Open/Closes Laser Shutter
#what_to_test = ['CCD','SkyScanner','FilterWheel', 'LaserShutter', 'Sequence', 'Sun', 'SkyAlert', 'gmail']

# What has been tested at LOW by JJM on June 13, 2023:
#	CCD
# 	FilterWheel
#	SkyAlert
#	LaserShutter
#	SkyScanner
#	Sun
#	Sequence
# 	gmail

#what_to_test = ['LaserShutter']
#what_to_test = ['SkyAlert']
what_to_test = ['Sequence']


powerControl = PowerControl(config['powerSwitchAddress'], config['powerSwitchUser'], config['powerSwitchPassword'])

if 'CCD' in what_to_test:
    powerControl.turnOn(config['AndorPowerPort'])
    logging.info('Initializing CCD')
    camera = getCamera("Andor")
    camera.setTemperature(-40)
    logging.info('Set temperature to -40 and cooling down')
    camera.turnOnCooler()
    print(camera.getTemperature())
    sleep(10)
    print(camera.getTemperature())
    sleep(10)
    print(camera.getTemperature())
    logging.info('Shutting down cooler')
    camera.shutDown()
    powerControl.turnOff(config['AndorPowerPort'])

if 'LaserShutter' in what_to_test:
    logging.info('Initializing LaserShutter')
    lasershutter = HIDLaserShutter(config['vendorId'], config['productId'])

    lasershutter.close_shutter()
    sleep(5)
    lasershutter.open_shutter()
    sleep(5)
    lasershutter.close_shutter()
    sleep(5)
    logging.info('Finished testing LaserShutter')

if 'FilterWheel' in what_to_test:
    powerControl.turnOn(config['FilterWheelPowerPort'])
    logging.info('Initializing FilterWheel')
    fw = FilterWheel(ip_address=filterwheel_config['ip_address'])
##    fw = FilterWheel(filterwheel_config['port_location'])
    logging.info('Homing Filterwheel')
    fw.home()
    logging.info('Going to positiion 2')
    fw.go(2)
    logging.info('Going to positiion 1')
    fw.go(1)
    logging.info('Going to positiion 0')
    fw.go(0)
    logging.info('Going to positiion 3')
    fw.go(3)
    logging.info('Turning off FilterWheel')
    powerControl.turnOff(config['FilterWheelPowerPort'])

if 'SkyScanner' in what_to_test:
    powerControl.turnOn(config['SkyScannerPowerPort'])
    logging.info('Initializing SkyScanner')
    skyscanner = SkyScanner(skyscan_config['max_steps'], skyscan_config['azi_offset'], skyscan_config['zeni_offset'], skyscan_config['azi_world'], skyscan_config['zeni_world'], skyscan_config['number_of_steps'], skyscan_config['port_location'])
    logging.info('Sending SkyScanner home')
    skyscanner.go_home()
    logging.info('Turning off SkyScanner')
    powerControl.turnOff(config['SkyScannerPowerPort'])

if 'SkyAlert' in what_to_test:
    sa = SkyAlert(config['skyAlertAddress'])
    logging.info(sa.getList())

if 'gmail' in what_to_test:
    sm = SendMail(config['email'], config['pickleCred'], config['gmailCred'], config['site'])

    print("sending mail")
    sm.send_error(["khanhn2@illinois.edu"], "Test connection")

if 'Sequence' in what_to_test:
    logging.info('Turning on SkyScanner and FilterWheel power')
    powerControl.turnOn(config['SkyScannerPowerPort'])
    powerControl.turnOn(config['FilterWheelPowerPort'])

    fw = FilterWheel(ip_address=filterwheel_config['ip_address'])
#    fw = FilterWheel(filterwheel_config['port_location'])
    skyscanner = SkyScanner(skyscan_config['max_steps'], skyscan_config['azi_offset'], skyscan_config['zeni_offset'], skyscan_config['azi_world'], skyscan_config['zeni_world'], skyscan_config['number_of_steps'], skyscan_config['port_location'])
    fw.home()

    logging.info('Sending SkyScanner home')
    skyscanner.go_home()

    # Loop through observations
    for observation in observations:
        logging.info('Moving SkyScanner to: %.2f, %.2f' % (observation['skyScannerLocation'][0], observation['skyScannerLocation'][1]))
        skyscanner.set_pos_real(observation["skyScannerLocation"][0], observation['skyScannerLocation'][1])
        world_az, world_zeni = skyscanner.get_world_coords()
        logging.info("The Sky Scanner has moved to azi: %.2f, and zeni: %.2f" %(world_az, world_zeni))

        # Move the filterwheel
        logging.info('Moving FilterWheel to: %d' % (observation['filterPosition']))
        fw.go(observation['filterPosition'])
        logging.info("Moved FilterWheel")
    
    logging.info('Moving to laser position')
    skyscanner.set_pos_real(config['azi_laser'],config['zen_laser'])
    world_az, world_zeni = skyscanner.get_world_coords()
    logging.info("The Sky Scanner has moved to azi: %.2f, and zeni: %.2f" %(world_az, world_zeni))

    # Move the filterwheel
    logging.info('Moving FilterWheel to: %d' % (observation['filterPosition']))
    fw.go(filterwheel_config['laser_position'])
    logging.info("Moved FilterWheel")

    logging.info('Turning off SkyScanner and FilterWheel power')
    powerControl.turnOff(config['SkyScannerPowerPort'])
    powerControl.turnOff(config['FilterWheelPowerPort'])

if 'Sun' in what_to_test:
    logging.info('Turning on SkyScanner power')
    powerControl.turnOn(config['SkyScannerPowerPort'])

    skyscanner = SkyScanner(skyscan_config['max_steps'], skyscan_config['azi_offset'], skyscan_config['zeni_offset'], skyscan_config['azi_world'], skyscan_config['zeni_world'], skyscan_config['number_of_steps'], skyscan_config['port_location'])

    logging.info('Sending SkyScanner home')
    skyscanner.go_home()

    # calculate the sun angle
    obs = ephem.Observer()
    obs.lat = str(config['latitude'])
    obs.lon = str(config['longitude'])
    obs.date = datetime.utcnow()
    sun = ephem.Sun(obs)
    sunAz = (sun.az.real)*180./np.pi
    sunZe = (np.pi/2 - sun.alt.real)*180./np.pi

    skyscanner.set_pos_real(sunAz, sunZe)
    logging.info("The Sky Scanner will be moved to azi: %.2f, and zeni: %.2f" %(sunAz, sunZe))
    world_az, world_zeni = skyscanner.get_world_coords()
    logging.info("The Sky Scanner has moved to azi: %.2f, and zeni: %.2f" %(world_az, world_zeni))

    logging.info('Turning off SkyScanner power')
    powerControl.turnOff(config['SkyScannerPowerPort'])
