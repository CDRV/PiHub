##################################################
# PiHub hardware utilities
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import os
import time
import logging
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