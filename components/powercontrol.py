import sys
import dlipower
import logging
import time

class PowerControl:
    def __init__(self, hostname="192.168.1.100", userid="admin", password="ionosphere") -> None:
        self.switch = dlipower.PowerSwitch(hostname=hostname, userid=userid, password=password, timeout=60, retries=5)
        if not self.switch.verify():
            logging.error("Can't talk to the switch")
        logging.info("Connected to power switch")

    def turnOn(self, port):
        res = self.switch.on(port)
#        if res == False:

        if self.switch.status(port) != 'ON':
            # The action hasn't completed yet, pause
            logging.debug("Trying to turn on " + str(port) + " an pausing")
            time.sleep(1)

        if self.switch.status(port) == 'ON':
            # dlipower returns False if the operation succeeded
            logging.info("Powered on port " + str(port))
        else:
            logging.error("Cannot power on port " + str(port))

    def turnOff(self, port):
        res = self.switch.off(port)
#        if res == False:

        if self.switch.status(port) != 'OFF':
            # The action hasn't completed yet, pause
            logging.debug("Trying to turn off " + str(port) + " an pausing")
            time.sleep(1)

        if self.switch.status(port) == 'OFF':
            logging.info("Powered off port " + str(port))
        else:
            logging.error("Cannot power off port " + str(port))

    def cycle(self, port):
        res = self.switch.cycle(port)
        if res == False:
            logging.info("Cycled port " + str(port))
        else:
            logging.error("Cannot cycle port " + str(port))
