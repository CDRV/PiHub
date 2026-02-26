##################################################
# PiHub hardware utilities
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import os
import time
import logging
import threading
import subprocess
from libs.utils.Network import Network


class PiHubHardware:

    @staticmethod
    def reset_cellular_network():
        logging.warning('Reset Cellular Network requested, but unavailable for that device.')
        # cmd = 'sh /home/pi/Desktop/PiHub/setup/pihub_startup.sh'
        # os.system(cmd)

    @staticmethod
    def reboot():
        # cmd_reboot = 'sudo reboot'
        # os.system(cmd_reboot)
        logging.warning('Reboot requested, but disabled for now...')

    @staticmethod
    def ensure_internet_is_available():
        lock = threading.Lock()
        lock.acquire()  # Ensure only one thread run the following code at a time

        logging.debug('Watchdog - checking Internet connection')
        if not Network.is_internet_connected():
            logging.warning('Internet is down... Trying to reboot cellular card.')
            # No internet connection... Try to reboot the cellular network
            # PiHubHardware.reset_cellular_network()
            time.sleep(5)  # Wait 5 seconds to see if network is coming back online or not
            if not Network.is_internet_connected():
                logging.warning('Reboot completed, but still no Internet...')
                # Still no internet connection - reboot the pi!
                # SB - 2025-02-05: Removed reboot to avoid infinite reboot loop
                # PiHubHardware.reboot()
            else:
                logging.info('Internet is back. All is fine.')

        lock.release()

    @staticmethod
    def wait_for_internet(timeout: int = 60):
        logging.info("Waiting for Internet connection... Timeout = " + str(timeout) + "s")
        while timeout > 0:
            if Network.is_internet_connected():
                logging.info("Internet connection OK!")
                return  # All is fine - back to normal operation
            time.sleep(5)
            timeout = timeout - 5

        logging.warning("No Internet connection - trying to reset...")
        PiHubHardware.ensure_internet_is_available()

    @staticmethod
    def wait_for_internet_infinite():
        logging.debug('Watchdog - checking Internet connection')
        while not Network.is_internet_connected():
            logging.warning('Internet is down... Trying to reboot cellular card.')
            # No internet connection... Try to reboot the cellular network
            # PiHubHardware.reset_cellular_network()
            time.sleep(60)  # Wait 60 seconds to see if network is coming back online or not
        logging.info('Internet is back. All is fine.')

    @staticmethod
    def has_usb_device(name: str) -> bool:
        # logging.debug('Checking for device ' + name)
        cmd = 'lsusb | grep ' + name
        output = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        return not (not output.stdout)

    @staticmethod
    def reboot_usb_hub():
        cmd = "sudo uhubctl -a2 -l1-1"
        output = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # logging.debug(output.stdout)
