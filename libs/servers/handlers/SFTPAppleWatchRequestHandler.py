from libs.servers.handlers.BaseAppleWatchRequestHandler import BaseAppleWatchRequestHandler
import logging


class SFTPAppleWatchRequestHandler(BaseAppleWatchRequestHandler):

    def setup(self):
        super().setup()

    def do_GET(self):
        super().do_GET()

    def do_POST(self):
        # Stop timer to send data, since we received new data
        if self.base_server.file_syncher_timer and self.base_server.file_syncher_timer.is_alive():
            self.base_server.file_syncher_timer.cancel()
            self.base_server.file_syncher_timer = None

        super().do_POST()
