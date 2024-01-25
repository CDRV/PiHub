from libs.servers.handlers.BaseAppleWatchRequestHandler import BaseAppleWatchRequestHandler
from opentera_libraries.device.DeviceComManager import DeviceComManager
import urllib.parse

import logging
import requests


class OpenTeraAppleWatchRequestHandler(BaseAppleWatchRequestHandler):

    def setup(self):
        super().setup()

    def do_GET(self):
        if self.path.startswith('/api/device'):
            logging.debug('Routing request to /api/device to OpenTera...')
            # Parse parameters from query
            query_params = urllib.parse.urlparse(self.path).query
            query_path = urllib.parse.urlparse(self.path).path
            params = urllib.parse.parse_qs(query_params)
            opentera_config = self.base_server.opentera_config

            if query_path.endswith('register'):
                device_com = DeviceComManager(server_url=opentera_config['hostname'],
                                              server_port=opentera_config['port'],
                                              allow_insecure=self.base_server.allow_insecure_server)
                if 'name' not in params or 'type_key' not in params:
                    self.send_error(400, 'Bad parameters')
                    return
                subtype_name = None
                device_name = params['name'][0]
                logging.info('Registering device "' + device_name + '"...')
                if 'subtype_name' in params:
                    subtype_name = params['subtype_name'][0]
                response = device_com.register_device(server_key=opentera_config['device_register_key'],
                                                      device_name=device_name,
                                                      device_type_key=params['type_key'][0],
                                                      device_subtype_name=subtype_name)
                if response.status_code == 200:
                    logging.info("Registered!")
                    # Save token for future use!
                    self.base_server.update_device_token(device_name, response.json()['device_token'])
                else:
                    logging.warning("Register failed.")
                self.forward_opentera_response(response)
            else:
                response = requests.get(url=self.base_server.opentera_server_url + query_path, params=query_params,
                                        headers=self.headers, verify=not self.base_server.allow_insecure_server)
                # Copy response from OpenTera
                self.forward_opentera_response(response)
                return

        # Catch token if available
        content_type = self.headers['Content-Type']
        if content_type == 'cdrv-cmd/Connect':
            if 'Device-Name' in self.headers and 'Device-Token' in self.headers:
                device_name = self.headers['Device-Name']
                device_token = self.headers['Device-Token']
                self.base_server.update_device_token(device_name, device_token)

        super().do_GET()

    def do_POST(self):
        super().do_POST()

    def forward_opentera_response(self, response: requests.Response):
        self.send_response_only(response.status_code)
        for header in response.headers:
            self.send_header(header, response.headers[header])
        self.end_headers()
        self.wfile.write(bytes(response.text, 'utf-8'))
