import sys
import logging
import time
import subprocess

# Only import dlipower if using the modern controller
try:
    import dlipower
except ImportError:
    pass

class PowerControl:
    def __init__(self, hostname="192.168.1.100", userid="admin", password="ionosphere", legacy_controller=False) -> None:
        self.hostname = hostname
        self.userid = userid
        self.password = password
        self.legacy_controller = legacy_controller
        
        if not self.legacy_controller:
            self.switch = dlipower.PowerSwitch(hostname=hostname, userid=userid, password=password, timeout=60, retries=5)
            if not self.switch.verify():
                logging.error("Can't talk to the switch")
            logging.info("Connected to power switch")
        else:
            # For legacy controller, we'll just log that we're using it
            logging.info("Using legacy controller with lpcperl.pl")
    
    def _run_legacy_command(self, port, action):
        """Run the legacy perl script to control the switch"""
        if port is None:
            return False
            
        # Construct the command
        command = f"/home/airglow/airglow/airglow-controller/lpcperl.pl {self.hostname} {self.userid}:{self.password} {port}{action}"
        
        try:
            # Run the command and capture output
            result = subprocess.run(command, shell=True, check=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True)
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Legacy controller command failed: {e}")
            return False
    
    def _get_legacy_status(self, port):
        """This would need implementation to check status in legacy mode"""
        # Note: The legacy perl script doesn't seem to have a status check based on the information provided
        # You would need to implement this based on how the lpcperl.pl script can report status
        # For now, we'll just return the expected status based on last action
        return None
            
    def turnOn(self, port):
        if port is None:
            return
            
        if self.legacy_controller:
            success = self._run_legacy_command(port, "on")
            if success:
                logging.info(f"Powered on port {port} (legacy controller)")
            else:
                logging.error(f"Cannot power on port {port} (legacy controller)")
        else:
            # Original implementation
            res = self.switch.on(port)
            if self.switch.status(port) != 'ON':
                # The action hasn't completed yet, pause
                logging.debug(f"Trying to turn on {port} and pausing")
                time.sleep(1)
            if self.switch.status(port) == 'ON':
                logging.info(f"Powered on port {port}")
            else:
                logging.error(f"Cannot power on port {port}")
    
    def turnOff(self, port):
        if port is None:
            return
            
        if self.legacy_controller:
            success = self._run_legacy_command(port, "off")
            if success:
                logging.info(f"Powered off port {port} (legacy controller)")
            else:
                logging.error(f"Cannot power off port {port} (legacy controller)")
        else:
            # Original implementation
            res = self.switch.off(port)
            if self.switch.status(port) != 'OFF':
                # The action hasn't completed yet, pause
                logging.debug(f"Trying to turn off {port} and pausing")
                time.sleep(1)
            if self.switch.status(port) == 'OFF':
                logging.info(f"Powered off port {port}")
            else:
                logging.error(f"Cannot power off port {port}")
    
    def cycle(self, port):
        if port is None:
            return
            
        if self.legacy_controller:
            # For the legacy controller, implement cycle as off, wait, on
            off_success = self._run_legacy_command(port, "off")
            if off_success:
                time.sleep(2)  # Wait for the device to properly power down
                on_success = self._run_legacy_command(port, "on")
                if on_success:
                    logging.info(f"Cycled port {port} (legacy controller)")
                else:
                    logging.error(f"Cannot complete cycle for port {port} - turn on failed (legacy controller)")
            else:
                logging.error(f"Cannot complete cycle for port {port} - turn off failed (legacy controller)")
        else:
            # Original implementation
            res = self.switch.cycle(port)
            if res == False:
                logging.info(f"Cycled port {port}")
            else:
                logging.error(f"Cannot cycle port {port}")
