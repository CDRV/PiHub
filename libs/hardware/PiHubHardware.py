##################################################
# PiHub hardware utilities
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import os
import time
import logging
import threading
from libs.utils.Network import Network


class PiHubHardware:

    @staticmethod
    def reset_cellular_network():
        cmd = 'sh /home/pi/Desktop/PiHub/setup/pihub_startup.sh'
        os.system(cmd)

    @staticmethod
    def reboot():
        cmd_reboot = 'sudo reboot'
        os.system(cmd_reboot)

    @staticmethod
    def ensure_internet_is_available():
        threading.Lock().acquire()  # Ensure only one thread run the following code at a time

        logging.debug('Watchdog - checking Internet connection')
        if not Network.is_internet_connected():
            logging.warning('Internet is down... Trying to reboot cellular card.')
            # No internet connection... Try to reboot the cellular network
            PiHubHardware.reset_cellular_network()
            time.sleep(5)  # Wait 5 seconds to see if network is coming back online or not
            if not Network.is_internet_connected():
                logging.warning('Reboot completed, but still no Internet... Rebooting...')
                # Still no internet connection - reboot the pi!
                PiHubHardware.reboot()
            logging.info('Internet is back. All is fine.')

        threading.Lock().release()

    @staticmethod
    def wait_for_internet(timeout: int = 60):
        logging.info("Waiting for Internet connection... Timeout = " + timeout + "s")
        while timeout > 0:
            if Network.is_internet_connected():
                logging.info("Internet connection OK!")
                return  # All is fine - back to normal operation
            time.sleep(5)
            timeout = timeout - 5

        logging.warning("No Internet connection - trying to reset...")
        PiHubHardware.ensure_internet_is_available()
