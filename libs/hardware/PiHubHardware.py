##################################################
# PiHub hardware utilities
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import os
import time


class PiHubHardware:

    @staticmethod
    def reset_cellular_network():
        cmd = 'sh /home/pi/Desktop/PiHub/setup/pihub_startup.sh'
        os.system(cmd)

    @staticmethod
    def reboot():
        cmd_reboot = 'sudo reboot'
        os.system(cmd_reboot)
