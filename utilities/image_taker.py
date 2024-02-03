from time import sleep
import h5py
from datetime import datetime
import logging


class Image_Helper:
    counter = None
    folderName = None
    camera = None
    site = None
    latitude = None
    longitude = None
    instrument = None
    XBinning = None
    YBinning = None
    def __init__(self, folderName, camera, site, latitude, longitude, instrument, xbin, ybin, skyAlert) -> None:
        self.counter = {  # JJM: NEED TO FIND A WAY TO SELF-INITIALIZE THESE IN CASE WE DEFINE A NEW TYPE
            "XG": 0,
            "XR": 0,
            "D": 0,
            "L": 0,
            "B": 0,
            "X0": 0,
            "X1": 0,
            "X2": 0,
            "X3": 0
        }
        self.folderName = folderName
        self.camera = camera
        self.site = site
        self.longitude = float(longitude)
        self.latitude = float(latitude)
        self.instrument = instrument
        self.XBinning = xbin
        self.YBinning = ybin
        self.skyAlert = skyAlert

    def save_image(self, type, imgData, exp, az, ze, startTime):
        data_files = h5py.File(self.folderName + '/' +
                               self.site + '_' + type + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.hdf5', 'w')
        # Log
        f = data_files.create_dataset("image", data=imgData)
        f.attrs['ExposureTime'] = exp
        # JJM THIS SHOULD BE THE AZ THE SKYCANNER ACTUAKKY WENT TO (JUST IN CASE IT DIDN'T REACH THE DESIRED LOCATONON, SO READ THE VALUE
        f.attrs['azAngle'] = az
        # JJM SAME AS ABOVE (READ THE VALUE FROM THE SKYSCANNER
        f.attrs['zeAngle'] = ze
        f.attrs['LocalTime'] = startTime 
        f.attrs['CCDTemperature'] = self.camera.getTemperature()
        f.attrs['SiteName'] = self.site
        f.attrs['SiteLatitude'] = self.latitude
        f.attrs['SiteLongitude'] = self.longitude
        f.attrs['Instrument'] = self.instrument
        f.attrs['XBinning'] = self.XBinning
        f.attrs['YBinning'] = self.YBinning

        # SkyAlert data
        f.attrs['AmbientTemperature (C)'] = self.skyAlert.getAmbientTemperature()
        f.attrs['OutsideTemperature (C)'] = self.skyAlert.getSkyTemperature()
        f.attrs['Pressure (Pa)'] = self.skyAlert.getPressure()
        f.attrs['Humidity (%)'] = self.skyAlert.getHumidity()
        # do we need wind speed, dampness, brightness? What unit? 


        data_files.close()
        self.counter[type] += 1

    def take_dark_image(self, exposure, az, ze):
        # closes shutter
        logging.info('Taking initial dark image')
        self.camera.setShutter(mode=2)
        self.camera.setExposureTime(exposure)
        startTime = str(datetime.now())
        self.camera.startAcquisition()
        sleep(exposure)
        while (self.camera.getStatus() == "DRV_ACQUIRING"):
            sleep(2)
        nparr = self.camera.getImage()
        self.save_image("D", nparr, exposure, az, ze, startTime)
        logging.info('Dark image taken')
        return nparr

    def take_bias_image(self, exposure, az, ze):
        # closes shutter
        logging.info('Taking initial bias image')
        self.camera.setShutter(mode=2)
        self.camera.setExposureTime(exposure)
        startTime = str(datetime.now())
        self.camera.startAcquisition()
        sleep(exposure)
        while (self.camera.getStatus() == "DRV_ACQUIRING"):
            sleep(2)
        nparr = self.camera.getImage()
        self.save_image("B", nparr, exposure, az, ze, startTime)
        logging.info('Initial bias image taken')
        return nparr

    def take_normal_image(self, image_tag, exposure, az, ze, skyscanner):
        # keeps shutter open by default
        self.camera.setShutter()
        self.camera.setExposureTime(exposure)
        startTime = str(datetime.now())
        self.camera.startAcquisition()
        sleep(exposure)
        while (self.camera.getStatus() == "DRV_ACQUIRING"):
            sleep(2)
        nparr = self.camera.getImage()
        azreal, zereal = skyscanner.get_world_coords()
        self.save_image(image_tag, nparr, exposure, azreal, zereal, startTime)
        return nparr

    # function for laser image

    def take_laser_image(self, exposure, skyscanner, lasershutter, az, zen, fw, fw_laser):
        skyscanner.set_pos_real(az, zen)
        # move filterwheel
        fw.go(fw_laser)
        lasershutter.open_shutter()
        self.camera.setShutter()
        self.camera.setExposureTime(exposure)
        startTime = str(datetime.now())
        self.camera.startAcquisition()
        sleep(exposure)
        while (self.camera.getStatus() == "DRV_ACQUIRING"):
            sleep(2)
        nparr = self.camera.getImage()
        lasershutter.close_shutter()

        azreal, zereal = skyscanner.get_world_coords()
        self.save_image("L", nparr, exposure, azreal, zereal, startTime)
        return nparr
