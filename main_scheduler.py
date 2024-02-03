import os
import sys
import logging
import signal
import scipy
import numpy
import pickle
from time import sleep
from datetime import datetime, timedelta
import smtplib, ssl
from config import config, skyscan_config, filterwheel_config
from schedule import observations

import utilities.time_helper
from utilities.image_taker import Image_Helper
from utilities.send_mail import SendMail
from utilities.get_IP import get_IP_from_MAC

from components.camera import getCamera
from components.shutterhid import HIDLaserShutter
from components.sky_scanner_keo import SkyScanner
from components.skyalert import SkyAlert
from components.powercontrol import PowerControl
from components.filterwheel import FilterWheel

try:
    # logger file
    log_name = config['log_dir'] + config['site'] + datetime.now().strftime('_%Y%m%d_%H%M%S.log')
    logging.basicConfig(filename=log_name, encoding='utf-8',
                        format='%(asctime)s %(message)s',  level=logging.INFO)


    timeHelper = utilities.time_helper.TimeHelper()
    sunrise = timeHelper.getSunrise()
    logging.info('Sunrise time set to ' + str(sunrise))
    sunset = timeHelper.getSunset()
    logging.info('Sunset time set to ' + str(sunset))

    # 30 min before house keeping time
    timeHelper.waitUntilHousekeeping(deltaMinutes=-30)

    # Turn on power
    powerControl = PowerControl(config['powerSwitchAddress'], config['powerSwitchUser'], config['powerSwitchPassword'])
    powerControl.turnOn(config['AndorPowerPort'])
    powerControl.turnOn(config['SkyScannerPowerPort'])
    powerControl.turnOn(config['LaserPowerPort'])

    # Filter wheel power (was a sequence before to reboot the Pi, but took that out
    powerControl.turnOn(config['FilterWheelPowerPort'])

    # Cycle the Cloud sensor power
    powerControl.turnOff(config['CloudSensorPowerPort'])
    sleep(5)
    powerControl.turnOn(config['CloudSensorPowerPort'])
    sleep(45)
    SkyAlert_IP = get_IP_from_MAC(config['skyAlertMAC'])
    if SkyAlert_IP is not None:
        config['skyAlertAddress'] = 'http://' + SkyAlert_IP + ':81'
        logging.info('Found SkyAlert at %s' % SkyAlert_IP)
    else:
        logging.info('Could not find SkyAlert after power cycle')

    # Make sure we can find the filterwheel
    filterwheel_serial = False
    filterwheel_IP = get_IP_from_MAC(filterwheel_config['MAC_address'])
    if filterwheel_IP is not None:
        filterwheel_config['ip_address'] = 'http://' + filterwheel_IP + ':8080/'
        filterwheel_serial = False
        logging.info('Found FilterWheel at %s' % filterwheel_IP)
    else:
        logging.info('Could not find the IP address for the filterwheel. Rebooting.')
        powerControl.turnOff(config['FilterWheelControlPowerPort'])
        sleep(5)
        powerControl.turnOn(config['FilterWheelControlPowerPort'])
        sleep(60)
        filterwheel_IP = get_IP_from_MAC(filterwheel_config['MAC_address'])
        if filterwheel_IP is not None:
            filterwheel_config['ip_address'] = 'http://' + filterwheel_IP + ':8080'
            filterwheel_serial = False
            logging.info('Found FilterWheel at %s' % filterwheel_IP)
        else:
            logging.info('Still cannot find IP address fo the filterwheel. Waiting...')
            wait_count = 0
            found = False
            while wait_count < 5 and found == False:
                wait_count = wait_count+1
                sleep(15)
                filterwheel_IP = get_IP_from_MAC(filterwheel_config['MAC_address'])
                if filterwheel_IP is not None:
                    filterwheel_config['ip_address'] = 'http://' + filterwheel_IP + ':8080'
                    filterwheel_serial = False
                    found = True
                    logging.info('Found Filterwheel at %s' % filterwheel_IP)
                else:
                    filterwheel_serial = True

    logging.info('Waiting until Housekeeping time: ' +
                str(timeHelper.getHousekeeping()))
    timeHelper.waitUntilHousekeeping()


    # Housekeeping
    lasershutter = HIDLaserShutter(config['vendorId'], config['productId'])
    skyscanner = SkyScanner(skyscan_config['max_steps'], skyscan_config['azi_offset'], skyscan_config['zeni_offset'], skyscan_config['azi_world'], skyscan_config['zeni_world'], skyscan_config['number_of_steps'], skyscan_config['port_location'])
    camera = getCamera("Andor")
    if filterwheel_serial:
        # Use the serial port
        logging.info('Opening Filterwheel serial port')
        fw = FilterWheel(port=filterwheel_config['port_location'])
    else:
        # Use the network (this is preferred!)
        logging.info('Opening Filterwheel network')
        fw = FilterWheel(ip_address=filterwheel_config['ip_address'])

    # Signal to response to interupt/kill signal
    def signal_handler(sig, frame):
        skyscanner.go_home()
        fw.go(filterwheel_config['park_position'])
        camera.turnOffCooler()
        camera.shutDown()
        powerControl = PowerControl(config['powerSwitchAddress'], config['powerSwitchUser'], config['powerSwitchPassword'])
        powerControl.turnOff(config['AndorPowerPort'])
        powerControl.turnOff(config['SkyScannerPowerPort'])
        powerControl.turnOff(config['LaserPowerPort'])
        powerControl.turnOff(config['FilterWheelPowerPort'])
        logging.info('Exiting')
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)


    skyscanner.go_home()
    fw.home()

    # Setup camera
    camera.setReadMode()
    camera.setImage(hbin=config['hbin'], vbin=config['vbin'])
    camera.setShiftSpeed()
    camera.setTemperature(config["temp_setpoint"])
    camera.turnOnCooler()
    logging.info('Set camera temperature to %.2f C' % config["temp_setpoint"])


    logging.info("Waiting for sunset: " + str(sunset))
    timeHelper.waitUntilStartTime()
    logging.info('Sunset time start')

    # Create data directroy based on the current sunset time
    data_folder_name = config['data_dir'] + sunset.strftime('%Y%m%d')
    logging.info('Creating data directory: ' + data_folder_name)
    isExist = os.path.exists(data_folder_name)
    if not isExist:
        os.makedirs(data_folder_name)

    imageTaker = Image_Helper(data_folder_name, camera,
                            config['site'], config['latitude'], config['longitude'], config['instr_name'], config['hbin'], config['vbin'], SkyAlert(config['skyAlertAddress']))

    # Take initial images
    if datetime.now() < (sunset + timedelta(minutes=10)):
        bias_image = imageTaker.take_bias_image(config["bias_expose"], 0, 0)
        dark_image = imageTaker.take_dark_image(config["dark_expose"], 0, 0)
        laser_image = imageTaker.take_laser_image(
            config["laser_expose"], skyscanner, lasershutter, config["azi_laser"], config["zen_laser"], fw, filterwheel_config["laser_position"])
        if config['laser_timedelta'] is not None:
            config['laser_lasttime'] = datetime.now()
    else:
        logging.info('Skipped initial images because we are more than 10 minutes after sunset')
        if config['laser_timedelta'] is not None:
            config['laser_lasttime'] = datetime.now()


    # Main loop
    while (datetime.now() <= sunrise):
        for observation in observations:
            if (datetime.now() >= sunrise):
                logging.info('Inside observation loop, but after sunrise! Exiting')
                break
            
            currThresholdMoonAngle = skyscanner.get_moon_angle(config['latitude'], config['longitude'], observation['skyScannerLocation'][0], observation['skyScannerLocation'][1])
            logging.debug('The current moon angle is: %.2f' % currThresholdMoonAngle)
            if (currThresholdMoonAngle <= config['moonThresholdAngle']):
                logging.info('The current moon angle is %.2f < the threshold angle of %.2f so skipping this observation (ze: %.2f, az: %.2f, filter: %d)' % (currThresholdMoonAngle, config['moonThresholdAngle'], observation['skyScannerLocation'][0], observation['skyScannerLocation'][1], observation['filterPosition']))
#                logging.info('The moonThreshold angle was too small. The current threshold moon angle is:  %.2f' % currThresholdMoonAngle + 
#                ' the current direction of telescope is az: %.2f ze: %.2f' % (
#                    observation['skyScannerLocation'][0], observation['skyScannerLocation'][1]))   
                continue

            logging.info('Moving SkyScanner to: %.2f, %.2f' % (
                observation['skyScannerLocation'][0], observation['skyScannerLocation'][1]))
            skyscanner.set_pos_real(
                observation["skyScannerLocation"][0], observation['skyScannerLocation'][1])
            world_az, world_zeni = skyscanner.get_world_coords()
            logging.info("The Sky Scanner has moved to azi: %.2f, and zeni: %.2f" %(world_az, world_zeni))

            # Move the filterwheel
            logging.info('Moving FilterWheel to: %d' % (observation['filterPosition']))
            fw.go(observation['filterPosition'])
            logging.info("Moved FilterWheel")

            logging.info('Taking sky exposure')

            if (observation['lastIntensity'] == 0 or observation['lastExpTime'] == 0):
                observation['exposureTime'] = observation['defaultExposureTime']
            else:
                observation['exposureTime'] = min(0.5*observation['lastExpTime']*(1 + observation['desiredIntensity']/observation['lastIntensity']),
                                                config['maxExposureTime'])

            logging.info('Calculated exposure time: {:.1f}'.format(observation['exposureTime']))

            # Take image
            new_image = imageTaker.take_normal_image(observation['imageTag'],
                                                    observation['exposureTime'],
                                                    observation['skyScannerLocation'][0],
                                                    observation['skyScannerLocation'][1], skyscanner)

            image_sub = scipy.signal.convolve2d(
                new_image[config['i1']:config['i2'], config['j1']:config['j2']], numpy.ones((config['N'], config['N']))/config['N']**2, mode='valid')
            image_intensity = (numpy.percentile(image_sub, 75) - numpy.percentile(
                image_sub, 25))*numpy.cos(numpy.deg2rad(observation['skyScannerLocation'][1]))

            observation['lastIntensity'] = image_intensity
            observation['lastExpTime'] = observation['exposureTime']

            logging.info('Image intensity: {:.2f}'.format(image_intensity))

            # Check if we should take a laser image
            logging.info('Time since last laser ' +  str(datetime.now() - config['laser_lasttime']))
            take_laser = (datetime.now() - config['laser_lasttime']) > config['laser_timedelta']
            logging.info('Take_laser is ' + str(take_laser))
            if take_laser:
                world_az, world_zeni = skyscanner.get_world_coords()
                logging.info("The Sky Scanner is pointed at laser position of azi: %.2f and zeni %.2f" %(world_az, world_zeni))
                logging.info('Taking laser image')
                laser_image = imageTaker.take_laser_image(
                    config["laser_expose"], skyscanner, lasershutter, config["azi_laser"], config["zen_laser"], fw, filterwheel_config["laser_position"])
                config['laser_lasttime'] = datetime.now()

    skyscanner.go_home()
    fw.go(filterwheel_config['park_position'])

    logging.info('Warming up CCD')
    camera.turnOffCooler()
    while (camera.getTemperature() < -20):
        logging.info('CCD Temperature: ' + str(camera.getTemperature()))
        sleep(10)

    logging.info('Shutting down CCD')
    camera.shutDown()

    powerControl = PowerControl(config['powerSwitchAddress'], config['powerSwitchUser'], config['powerSwitchPassword'])
    powerControl.turnOff(config['AndorPowerPort'])
    powerControl.turnOff(config['SkyScannerPowerPort'])
    powerControl.turnOff(config['LaserPowerPort'])
    powerControl.turnOff(config['FilterWheelPowerPort'])

    logging.info('Executed flawlessly, exitting')

except Exception as e:
    logging.error(e)

    logging.error('Turning off components')
    powerControl = PowerControl(config['powerSwitchAddress'], config['powerSwitchUser'], config['powerSwitchPassword'])
    powerControl.turnOff(config['AndorPowerPort'])
    powerControl.turnOff(config['SkyScannerPowerPort'])
    powerControl.turnOff(config['LaserPowerPort'])
    powerControl.turnOff(config['FilterWheelPowerPort'])

#    sm = SendMail(config['email'], config['pickleCred'], config['gmailCred'], config['site'])
#    
#    print("sending mail")
#    sm.send_error(config['receiverEmails'], e)

    
