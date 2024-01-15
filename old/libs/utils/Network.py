##################################################
# PiHub network monitoring and utilities
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import urllib.error
from urllib import request


class Network:

    @staticmethod
    def is_internet_connected() -> bool:
        try:
            request.urlopen(url='https://www.google.ca', timeout=5)
            return True
        except urllib.error.URLError:
            return False
