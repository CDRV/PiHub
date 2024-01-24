from libs.servers.handlers.BaseAppleWatchRequestHandler import BaseAppleWatchRequestHandler
import logging


class OpenTeraAppleWatchRequestHandler(BaseAppleWatchRequestHandler):

    def setup(self):
        super().setup()

    def do_GET(self):
        if self.path.startswith('/api/device'):
            if self.path.endswith('register'):
                # Do a device register
                pass
        super().do_GET()

    def do_POST(self):
        super().do_POST()
