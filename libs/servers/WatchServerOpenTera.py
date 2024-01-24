from libs.servers.WatchServerBase import WatchServerBase
from libs.servers.handlers.OpenTeraAppleWatchRequestHandler import OpenTeraAppleWatchRequestHandler

import logging
import os
import threading


class WatchServerOpenTera(WatchServerBase):

    def __init__(self, server_config: dict, opentera_config: dict):

        # Setup request handler
        request_handler = OpenTeraAppleWatchRequestHandler

        super().__init__(server_config=server_config, request_handler=request_handler)
        self.opentera_config = opentera_config

    def run(self):
        super().run()

    def new_file_received(self, filename: str):
        logging.error(self.__class__.__name__ + ' - TODO - Handle file!')
