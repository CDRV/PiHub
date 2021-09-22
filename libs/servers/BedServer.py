##################################################
# PiHub main communication server
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
from Globals import logger

import threading
import time


class BedServer(threading.Thread):

    def __init__(self, server_config: dict):
        self.port = server_config['port']
        self.hostname = server_config['hostname']
        self.data_path = server_config['data_path']
        self.is_running = False
        super().__init__()

    def run(self):
        logger.log_info('BedServer starting...')
        try:
            self.is_running = True
            while self.is_running:
                time.sleep(2)
                print("BedServer Thread: " + threading.currentThread().getName())

        finally:
            print(threading.currentThread().getName() + " ended.")

    def stop(self):
        self.is_running = False
