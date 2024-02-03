import time
import serial
from time import sleep
import logging
import hid

class HIDLaserShutter():
    pid = None
    vid = None
    def __init__(self, vendorId=0x0461, productId=0x0030):
        self.vid = vendorId
        self.pid = productId

        logging.info(f'Initializing USB Laser Shutter')

        with hid.Device(self.vid, self.pid) as h:
            logging.info(f'Laser Shutter Initilized')
            logging.info(f'Device manufacturer: {h.manufacturer}')
            logging.info(f'Product: {h.product}')

    def open_shutter(self):
        with hid.Device(self.vid, self.pid) as h:
            data = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            h.write(data)
            sleep(1)
            data = bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            h.write(data)
            sleep(1)

    def close_shutter(self):
        with hid.Device(self.vid, self.pid) as h:
            data = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            h.write(data)
            sleep(1)
