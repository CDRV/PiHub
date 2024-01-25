from libs.servers.WatchServerBase import WatchServerBase
from libs.servers.handlers.OpenTeraAppleWatchRequestHandler import OpenTeraAppleWatchRequestHandler

import logging
import os
import threading
import json
import datetime


class WatchServerOpenTera(WatchServerBase):

    _device_tokens = {}     # Mapping of devices names and tokens
    _device_timeouts = {}   # Timers of devices, since a watch can "disappear" and not send a "disconnect" command

    def __init__(self, server_config: dict, opentera_config: dict):

        # Setup request handler
        request_handler = OpenTeraAppleWatchRequestHandler

        super().__init__(server_config=server_config, request_handler=request_handler)
        self.opentera_config = opentera_config
        self.opentera_server_url = ('https://' + self.opentera_config['hostname'] + ':' +
                                    str(self.opentera_config['port']))
        self.allow_insecure_server = (self.opentera_config['hostname'] == 'localhost' or
                                      self.opentera_config['hostname'] == '127.0.0.1')

    def run(self):
        super().run()

    def update_device_token(self, device_name: str, token: str):
        self._device_tokens[device_name] = token

    def new_file_received(self, device_name: str, filename: str):
        # Start timeout timer in case device doesn't properly disconnect
        if device_name in self._device_timeouts:
            # Stop previous timer
            self._device_timeouts[device_name].cancel()

        # self._device_timeouts[device_name] = threading.Timer(300, self.initiate_opentera_transfer, device_name)
        # self._device_timeouts[device_name].start()

    def initiate_opentera_transfer(self, device_name: str):
        logging.info("WatchServerOpenTera: Initiating data transfer for " + device_name + "...")
        if device_name in self._device_timeouts:
            # Stop timer if needed
            self._device_timeouts[device_name].cancel()
            del self._device_timeouts[device_name]

        # Get base folder path
        base_folder = self.data_path + '/ToProcess/' + device_name
        base_folder = base_folder.replace('/', os.sep)
        if not os.path.isdir(base_folder):
            logging.error('Unable to locate data folder ' + base_folder)
            return

        for (dir_path, dir_name, files) in os.walk(base_folder):

            # Read session.oimi file
            session_file = os.path.join(dir_path, 'session.oimi')
            session_file = session_file.replace('/', os.sep)
            if not os.path.isfile(session_file):
                logging.error('No session file in ' + dir_path)
                continue

            with open(session_file) as f:
                session_data = f.read()

            session_data_json = json.loads(session_data)

            # Read watch_logs.txt file
            log_file = os.path.join(dir_path, '/watch_logs.txt')
            log_file = log_file.replace('/', os.sep)
            if not os.path.isfile(log_file):
                logging.error('No watch logs file in ' + dir_path)
                continue

            with open(session_file) as f:
                logs_data = f.read().splitlines()

            if len(logs_data) < 2:
                logging.info('Empty log file - ignoring...')
                self.move_folder(dir_path, dir_path.replace('ToProcess', 'Rejected'))
                continue

            # Compute duration
            first_timestamp = logs_data[0].split('\t')[0]
            last_timestamp = logs_data[-1].split('\t')[0]
            duration = float(last_timestamp) - float(first_timestamp)
            if duration <= self.minimal_dataset_duration:
                logging.info('Rejected folder ' + dir_path + ': dataset too small.')
                self.move_folder(dir_path, dir_path.replace('ToProcess', 'Rejected'))
                continue

            # Create session info structure
            if 'timestamp' in session_data_json:
                session_name = session_data_json['timestamp']
                session_starttime = datetime.datetime.fromisoformat(session_data_json['timestamp'].replace('_', ' '))
            else:
                logging.warning('No session timestamp found - using current time')
                session_name = device_name
                session_starttime = datetime.datetime.isoformat()

            session_info = {'id_session': 0, 'session_name': session_name, 'session_start_datetime': session_starttime,
                            'session_duration': duration}

            # Create session events

            # Upload all files to FileTransfer service
