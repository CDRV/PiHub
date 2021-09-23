##################################################
# PiHub base class for servers
##################################################
# Authors: Simon Brière, Eng. MASc.
##################################################

import threading


class BaseServer(threading.Thread):

    def __init__(self, server_config: dict):
        self.port = server_config['port']
        self.hostname = server_config['hostname']
        self.data_path = server_config['data_path']
        self.is_running = False
        super().__init__()
        self.setName(self.__class__.__name__ + 'Thread')

    def stop(self):
        self.is_running = False
