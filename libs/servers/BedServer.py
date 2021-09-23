##################################################
# PiHub main bed communication server
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
from libs.servers.BaseServer import BaseServer
import time
import logging


class BedServer(BaseServer):

    def __init__(self, server_config: dict):
        super().__init__(server_config=server_config)

    def run(self):
        logging.info('BedServer starting...')
        logging.info("BedServer started.")
        try:
            self.is_running = True
            while self.is_running:
                time.sleep(2)
                print("BedServer Thread: " + self.getName())

        finally:
            logging.info("BedServer stopped.")

