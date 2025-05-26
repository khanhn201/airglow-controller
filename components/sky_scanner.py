from asyncore import file_dispatcher
from inspect import CO_VARKEYWORDS
from config import config, skyscan_config
import sunau
import sys
import logging
import serial
import keyboard
from sshkeyboard import listen_keyboard, stop_listening
import time
from time import sleep
import ephem
import numpy as np
from math import pi
import datetime
from configScripts import configWriter

class SkyScanner():
    ser = None
    max_steps = None
    azi_offset = None
    zeni_offset = None
    azi_world = None
    zeni_world = None
    number_of_steps = None
    port_location = None

    def __init__(self, MaxSteps, AziOffset, ZeniOffset, AziWorld, ZeniWorld, NumberOfSteps, Port):
        self.max_steps = MaxSteps
        self.azi_offset = AziOffset
        self.zeni_offset = ZeniOffset
        self.azi_world = AziWorld
        self.zeni_world = ZeniWorld
        self.number_of_steps = NumberOfSteps
        self.port_location = Port
        try:
            self._openSerial()
            logging.info('Initialized SkyScanner')
        except:
            logging.info("Can't open serial port")

    def set_pos_azi(self, azi_machine_step):
        strr = 'a=%d ' % azi_machine_step
        self.ser.write(strr.encode())
        self.ser.write('GOSUB4 '.encode())
        process_az = self.ser.readline().decode()

    def set_pos_zeni(self, zeni_machine_step):
        strr = 'z=%d ' % zeni_machine_step
        self.ser.write(strr.encode())
        self.ser.write('GOSUB4 '.encode())
        process_az = self.ser.readline().decode()

    def set_pos(self, azi, zeni):
        self.ser.write(('a=%d ' % azi).encode())
        self.ser.write(('z=%d ' % zeni).encode())
        self.ser.write('GOSUB4 '.encode())
        process_az = self.ser.readline().decode()
        azi1, zeni1 = self.get_curr_coords()
        logging.info("Moving Skyscanner to Azi Machine Step: ", azi, " Zeni Machine Step: ", zeni)
        count = 0
        while (azi != azi1 or zeni != zeni1):
            # print(azi, azi1, zeni, zeni1)
            logging.debug("Current Azi Pos:", azi1, " ||||  Target Azi Pos:", azi)
            logging.debug("Current Zeni Pos:", zeni1, " ||||  Target Zeni Pos", zeni)

            azi1, zeni1 = self.get_curr_coords()
            sleep(2)
            #print("\n")

            count = count+1
            if count > 10:
                #print('resending commands')
                count = 0
                self.ser.write(('a=%d ' % azi).encode())
                self.ser.write(('z=%d ' % zeni).encode())
                self.ser.write('GOSUB4 '.encode())
                process_az = self.ser.readline().decode()

        sleep(3)
        #print("Finished Moving")

    def set_pos_real(self, azi_world, zeni_world):
        azi, zeni = self.convert_to_machine_steps(azi_world, zeni_world)
        #print("THIS is where I am moving", azi, zeni)
        logging.info("SkyScanner moving to azi: %.2f, and zeni: %.2f" %(azi_world, zeni_world))
        logging.info("SkyScanner moving to machine step azi: %.2f, and zeni: %.2f" %(azi, zeni))
        self.ser.write(('a=%d ' % azi).encode())
        self.ser.write(('z=%d ' % zeni).encode())
        self.ser.write(('GOSUB4 ').encode())
        process_az = self.ser.readline().decode()
        azi1, zeni1 = self.get_curr_coords()
        count = 0
        while (azi != azi1 or zeni != zeni1):
            logging.debug('set_pos_real while loop (goal, actual) az = (%.2f %.2f), ze = (%.2f %.2f)' % (azi, azi1, zeni, zeni1))
            azi1, zeni1 = self.get_curr_coords()
            sleep(2)
            #print("Waiting ", count)
            
            count = count+1
            if count > 10:
                print('resending commands')
                logging.info('SkyScanner had to resend commands')
                count = 0
                self.ser.write(('a=%d ' % azi).encode())
                self.ser.write(('z=%d ' % zeni).encode())
                self.ser.write('GOSUB4 '.encode())
                process_az = self.ser.readline().decode()


        azi1, zeni1 = self.get_curr_coords()
        azi_curr, zeni_curr = self.get_world_coords()
        logging.info("SkyScanner current location azi: %.2f, and zeni: %.2f" %(azi_curr, zeni_curr))
        logging.info("SkyScanner current machine step azi: %.2f, and zeni: %.2f" %(azi1, zeni1))
        #print("Finished Moving")




# do not use offset

# read config file_dispatche

# find the sun Coords

# point sky scanner ot that location

# call jog function (commnand line inputs using arrows )

# once sun is found give button push and set new coords of sun

# set differnce of where it thinks sun is versus where the motors are

# written to config file -.45

    def convert_to_machine_steps(self, azi_world, zeni_world):
        azi = -azi_world - self.azi_offset
        zeni = (-zeni_world) - self.zeni_offset + 180
        azi_machine_step = round((self.max_steps / 360) * azi)
        zeni_machine_step = round((self.max_steps / 360) * zeni)
        azi_machine_step = self.max_steps - (azi_machine_step % self.max_steps)
        zeni_machine_step = zeni_machine_step % self.max_steps
        print(azi_machine_step, zeni_machine_step)
        return azi_machine_step, zeni_machine_step

    def convert_sun_to_machine_steps(self, sun_location_azi, sun_location_zeni):
        azi = -sun_location_azi - self.azi_offset
        zeni = (-sun_location_zeni) - self.zeni_offset + 180
        azi_machine_step = round((self.max_steps / 360) * azi)
        zeni_machine_step = round((self.max_steps / 360) * zeni)
        azi_machine_step = self.max_steps - (azi_machine_step % self.max_steps)
        zeni_machine_step = zeni_machine_step % self.max_steps
        return azi_machine_step, zeni_machine_step

    def convert_sun_to_machine_steps_no_offset(self, sun_location_azi, sun_location_zeni):
        azi = -sun_location_azi
        zeni = (-sun_location_zeni)  + 180
        azi_machine_step = round((self.max_steps / 360) * azi)
        zeni_machine_step = round((self.max_steps / 360) * zeni)
        azi_machine_step = self.max_steps - (azi_machine_step % self.max_steps)
        zeni_machine_step = zeni_machine_step % self.max_steps
        return azi_machine_step, zeni_machine_step
    

    def convert_machine_step_to_degrees(self, machine_step):
        deg = (machine_step / self.max_steps) * (360.0) 
        return deg

    def get_world_coords(self):
        azi, zeni = self.get_curr_coords()
        world_az = self.convert_machine_step_to_degrees(azi) - self.azi_offset
        world_zeni = -self.convert_machine_step_to_degrees(zeni) - self.zeni_offset + 180
        return world_az, world_zeni



    def jog(self, sun_azi, sun_zeni, incrementAzi, incrementZeni, timeout_time):
        print("Jogging to the coordinants of the sun.  Azi: %f" % sun_azi + " Zeni: %f" %sun_zeni + " Please wait.\n")
        sun_azi_offset = 0
        sun_zeni_offset = 0
        machine_sun_azi, machine_sun_zeni = self.convert_sun_to_machine_steps_no_offset(sun_azi, sun_zeni)
        incrementMachineStepsAzi = round((self.max_steps / 360) * incrementAzi)
        incrementMachineStepsZeni = round((self.max_steps / 360) * incrementZeni)
        self.set_pos(machine_sun_azi, machine_sun_zeni)
        while (True):
            curr_az, curr_zen = self.get_curr_coords()
            azi_world_coords, zeni_world_coords = self.get_world_coords()
            print( "\nCurrent Azi Machine Step: ", curr_az, "   Current Azi Degrees (Including Previous Offset):", azi_world_coords)
            print("Current Zeni Machine Step: ", curr_zen, "   Current Zeni Degrees (Including Previous Offset): ", zeni_world_coords)
            if (curr_az == machine_sun_azi and machine_sun_zeni == curr_zen):
                break
        curr_az, curr_zen = self.get_curr_coords()
        print(
            "\nFinished moving to the sun's location - azi coord: %s"  %curr_az  + " zeni coord: %s. \n Use the arrow keys to move the position of the Sky Scanner (azi is left/right. Zeni is up/down). \n Press s to save current offset coords to config. \n Press q to exit out of jog." %curr_zen)
        

        def press(key):
            nonlocal sun_azi_offset
            nonlocal sun_zeni_offset
            while True:
                print("Use Arrow Keys To Move")
                isTimeoutSucceeded = True
                curr_az, curr_zen = self.get_curr_coords()
                if key == 'q':
                    print("Exited Jog")
                    stop_listening()
                    return
                elif key == 'left':
                    self.set_pos_azi(curr_az - incrementMachineStepsAzi)
                    sleep(2)
                    timeout = timeout_time
                    timeout_start = time.time()
                    while (time.time() < timeout_start + timeout):
                        curr_az1, curr_zen1 = self.get_curr_coords()
                        # print(curr_az, curr_az1)
                        if (curr_az - incrementMachineStepsAzi == curr_az1):
                            isTimeoutSucceeded = False
                            print("Jogged to %f degrees azi" %self.convert_machine_step_to_degrees(curr_az1))
                            sun_azi_offset -= incrementMachineStepsAzi
                            print("\ncurrent azi offset: %f" % sun_azi_offset +  "        previous Config Azi offset: %f" % self.azi_offset +  "\n current zeni offset: %f" % sun_zeni_offset + "        previous Config Zeni offset: %f"  %self.zeni_offset)

                            break
                    if isTimeoutSucceeded:
                        print("the skyscanner was not able to move to the correct position due to the timeout, please check the logs for errors")
                    return
                elif key == 'right':
                    self.set_pos_azi(curr_az + incrementMachineStepsAzi)
                    sleep(2)
                    timeout = timeout_time
                    timeout_start = time.time()
                    while (time.time() < timeout_start + timeout):
                        curr_az1, curr_zen1 = self.get_curr_coords()
                        # print(curr_az, curr_az1)
                        if (curr_az + incrementMachineStepsAzi == curr_az1):
                            isTimeoutSucceeded = False
                            print("Jogged to %f degrees azi" %self.convert_machine_step_to_degrees(curr_az1))
                            sun_azi_offset += incrementMachineStepsAzi
                            print("\ncurrent azi offset: %f" % sun_azi_offset +  "        previous Config Azi offset: %f" % self.azi_offset +  "\ncurrent zeni offset: %f" % sun_zeni_offset + "        previous Config Zeni offset: %f"  %self.zeni_offset)

                            break
                    if isTimeoutSucceeded:
                        print("the skyscanner was not able to move to the correct position, please check the logs for errors")
                    return
                elif key == 'down':
                    self.set_pos_zeni(curr_zen - incrementMachineStepsZeni)
                    sleep(2)
                    timeout = timeout_time
                    timeout_start = time.time()
                    while (time.time() < timeout_start + timeout):
                        curr_az1, curr_zen1 = self.get_curr_coords()
                        # print(curr_zen, curr_zen1)
                        if (curr_zen - incrementMachineStepsZeni == curr_zen1):
                            isTimeoutSucceeded = False
                            print("Jogged to %f degrees zeni" %self.convert_machine_step_to_degrees(curr_zen1))
                            sun_zeni_offset -= incrementMachineStepsZeni
                            print("\ncurrent azi offset: %f" % sun_azi_offset +  "        previous Config Azi offset: %f" % self.azi_offset +  "\n current zeni offset: %f" % sun_zeni_offset + "        previous Config Zeni offset: %f"  %self.zeni_offset)

                            break
                    if isTimeoutSucceeded:
                        print("the skyscanner was not able to move to the correct position, please check the logs for errors")
                    return
                elif key == 'up':
                    self.set_pos_zeni(curr_zen + incrementMachineStepsZeni)
                    sleep(2)
                    timeout = timeout_time
                    timeout_start = time.time()
                    while (time.time() < timeout_start + timeout):
                        curr_az1, curr_zen1 = self.get_curr_coords()
                        # print(curr_zen, curr_zen1)
                        if (curr_zen + incrementMachineStepsZeni == curr_zen1):
                            isTimeoutSucceeded = False
                            print("Jogged to %f degrees zeni" %self.convert_machine_step_to_degrees(curr_zen1))
                            sun_zeni_offset += incrementMachineStepsZeni
                            print("\ncurrent azi offset: %f" % sun_azi_offset +  "        previous Config Azi offset: %f" % self.azi_offset +  "\n current zeni offset: %f" % sun_zeni_offset + "        previous Config Zeni offset: %f"  %self.zeni_offset)

                            break
                    if isTimeoutSucceeded:
                        print("the skyscanner was not able to move to the correct position, please check the logs for errors")
                    return
                elif key == 's':
                    print("Saving Coordinants")
                    azi_degree_offset = (sun_azi_offset / self.max_steps) * (360) 
                    zeni_degree_offset = (sun_zeni_offset / self.max_steps) * (360)
                    print("azi degree offset %.2f" %azi_degree_offset + "zeni degree offset %.2f " %zeni_degree_offset)
                    configWriter.write_config(azi_degree_offset, zeni_degree_offset)
                    return

                 
        listen_keyboard(
            on_press=press,
            until="space",
            # on_release=release,
        )    
        return



    # def get_home_coords(self):
    #     '''Gets target position of SmartMotor'''
    #     self.ser.write('RPA '.encode())
    #     process_az = self.ser.readline().decode()
    #     print(process_az)
    #     split_by_command_numbers = process_az.split(' ')
    #     split_by_hash = split_by_command_numbers[1].split('\r')
    #     print(split_by_hash)
    #     # print(split_by_hash)
    #     ze = int(split_by_hash[0])
    #     az = int(split_by_hash[1])
    #     return az, ze

    def go_home(self):
        logging.info('Homing Skyscanner')
        self.ser.write('GOSUB5 '.encode())
        sleep(20)
        print("Finished Moving")
        logging.info('Homed Skyscanner')
        print("Finished Moving SkyScanner to Home Position")

    def get_curr_coords(self):
        '''Gets target position of SmartMotor'''
        self.ser.write('RPA'.encode())
        process_az = self.ser.readline().decode()
        #print('\nget_curr_coords process_az ', process_az)
        split_by_command_numbers = process_az.split(' ')
        split_by_hash = split_by_command_numbers[1].split('\r')
        #print('get_curr_coords split_by_hash (az, az) ', split_by_hash)
        ze = int(split_by_hash[0])
        az = int(split_by_hash[1])
        return az, ze

    def _openSerial(self):
        '''opens serial port and sets handle'''
        self.ser = serial.Serial(port=self.port_location, baudrate=9600,
                                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                 bytesize=serial.EIGHTBITS, timeout=1)

    def _closeSerial(self):
        self.ser.close()

    def stopMotor(self):
        self.ser.write('X ')

    # code used from:  https://github.com/bharding512/airglowrsss/blob/bc51cfa6e00566cad073e419ae66b3d5f4a9b57a/Python/modules/FPI.py#L1161
    def get_moon_angle(self, lat, lon, az, ze):
        obs = ephem.Observer()
        obs.lat = str(lat)
        obs.lon = str(lon)
        obs.date = datetime.datetime.utcnow()
        moon = ephem.Moon(obs)
        moonAz = moon.az.real
        moonZe = pi/2 - moon.alt.real
        a = np.cos(az*pi/180)*np.sin(ze*pi/180)
        b = np.sin(az*pi/180)*np.sin(ze*pi/180)
        aMoon = np.cos(moonAz)*np.sin(moonZe)
        bMoon = np.sin(moonAz)*np.sin(moonZe)
        moonAngle = np.arccos(a*aMoon + b*bMoon + np.cos(ze*pi/180) * np.cos(moonZe))
        return moonAngle*180./pi
    


    
