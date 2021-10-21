##################################################
# PiHub base class for servers
##################################################
# Authors: Simon Brière, Eng. MASc.
##################################################

import threading
from os import makedirs
import logging


class BaseServer(threading.Thread):

    def __init__(self, server_config: dict):
        self.port = server_config['port']
        self.hostname = server_config['hostname']
        self.data_path = server_config['data_path']
        self.is_running = False
        super().__init__()
        self.setName(self.__class__.__name__ + 'Thread')

        # Create base data path is missing
        try:
            makedirs(name=self.data_path, exist_ok=True)
        except OSError as exc:
            logging.error('Error creating ' + self.data_path + ': ' + exc.strerror)
            raise

    def stop(self):
        self.is_running = False
