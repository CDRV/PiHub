from libs.servers.WatchServerBase import WatchServerBase
from libs.servers.handlers.OpenTeraAppleWatchRequestHandler import OpenTeraAppleWatchRequestHandler

from opentera_libraries.device.DeviceComManager import DeviceComManager
import opentera_libraries.device.DeviceAPI as DeviceAPI
from cryptography.fernet import Fernet

import logging
import os
import threading
import json
import datetime


class WatchServerOpenTera(WatchServerBase):

    _device_tokens = {}     # Mapping of devices names and tokens
    _device_timeouts = {}   # Timers of devices, since a watch can "disappear" and not send a "disconnect" command
    file_syncher_timer = None

    def __init__(self, server_config: dict, opentera_config: dict):

        # Setup request handler
        request_handler = OpenTeraAppleWatchRequestHandler

        super().__init__(server_config=server_config, request_handler=request_handler)
        self.opentera_config = opentera_config
        self.opentera_server_url = ('https://' + self.opentera_config['hostname'] + ':' +
                                    str(self.opentera_config['port']))
        self.allow_insecure_server = (self.opentera_config['hostname'] == 'localhost' or
                                      self.opentera_config['hostname'] == '127.0.0.1')

        # Load cryptographic key (to encrypt tokens, for example)
        if not os.path.isfile('config/secure_opentera'):
            # Create key
            logging.info('WatchServerOpenTera: Generating encryption key...')
            self.secure_key = Fernet.generate_key()
            with open('config/secure_opentera', 'wb') as f:
                f.write(self.secure_key)
        else:
            with open('config/secure_opentera', 'rb') as f:
                self.secure_key = f.read()

        # Open token file and decrypt tokens
        self.load_tokens()

    def run(self):
        # Check if all files are on sync on the server (after the main server has started)
        self.file_syncher_timer = threading.Timer(1, self.sync_files)
        self.file_syncher_timer.start()

        super().run()

    def load_tokens(self):
        tokens_file = os.path.join(self.data_path, 'tokens')
        if os.path.isfile(tokens_file):
            # Load tokens from file
            with open(tokens_file, 'rb') as f:
                tokens = f.read()

            # Decrypt tokens
            fernet = Fernet(self.secure_key)
            device_tokens = fernet.decrypt(tokens).decode()
            self._device_tokens = json.loads(device_tokens.replace('\'', '"'))

    def save_tokens(self):
        tokens_file = os.path.join(self.data_path, 'tokens')
        # Encrypt tokens
        fernet = Fernet(self.secure_key)
        with open(tokens_file, 'wb') as f:
            f.write(fernet.encrypt(str(self._device_tokens).encode()))

    def update_device_token(self, device_name: str, token: str):
        update_required = device_name not in self._device_tokens
        if device_name in self._device_tokens and self._device_tokens[device_name] != token:
            update_required = True
        if update_required:
            self._device_tokens[device_name] = token
            self.save_tokens()

    def new_file_received(self, device_name: str, filename: str):
        # Start timeout timer in case device doesn't properly disconnect
        if device_name in self._device_timeouts:
            # Stop previous timer
            self._device_timeouts[device_name].cancel()

        # Starts a timeout timer in case the device doesn't properly disconnect (and thus trigger the transfer)
        self._device_timeouts[device_name] = threading.Timer(300, self.initiate_opentera_transfer,
                                                             kwargs={'device_name': device_name})
        self._device_timeouts[device_name].start()

    def device_disconnected(self, device_name: str):
        self.initiate_opentera_transfer(device_name)

    def sync_files(self):
        logging.info("WatchServerOpenTera: Checking if any pending transfers...")
        # Get base folder path
        base_folder = os.path.join(self.data_path, 'ToProcess')
        for device_name in os.listdir(base_folder):
            self.initiate_opentera_transfer(device_name)

        logging.info("All done!")

    def initiate_opentera_transfer(self, device_name: str):
        logging.info("WatchServerOpenTera: Initiating data transfer for " + device_name + "...")
        if device_name in self._device_timeouts:
            # Stop timer if needed
            self._device_timeouts[device_name].cancel()
            del self._device_timeouts[device_name]

        # Get base folder path
        base_folder = os.path.join(self.data_path, 'ToProcess', device_name)
        if not os.path.isdir(base_folder):
            logging.error('Unable to locate data folder ' + base_folder)
            return

        # Create OpenTera com module
        device_com = DeviceComManager(self.opentera_config['hostname'], self.opentera_config['port'],
                                      self.allow_insecure_server)
        if device_name not in self._device_tokens:
            logging.error('No OpenTera token for ' + device_name + ' - aborting transfer.')
            return

        device_com.token = self._device_tokens[device_name]

        # Do device login
        response = device_com.do_get(DeviceAPI.ENDPOINT_DEVICE_LOGIN)
        if response.status_code != 200:
            logging.error('OpenTera: Unable to login device ' + device_name + ': ' + str(response.status_code) +
                          ' - ' + response.text.strip())
            return

        device_infos = response.json()['device_info']
        participants_infos = response.json()['participants_info']
        session_types_infos = response.json()['session_types_info']

        if len(participants_infos) == 0:
            logging.error('No participant assigned to this device - will not transfer until this is fixed.')
            return

        # Find correct session type to use
        possible_session_types_ids = [st['id_session_type'] for st in session_types_infos
                                      if st['session_type_category'] == 2]  # Filter data collect session types
        if len(possible_session_types_ids) == 0:
            logging.error('No session types available to this device - will not transfer until this is fixed.')
            return

        id_session_type = self.opentera_config['default_session_type_id']
        if id_session_type not in possible_session_types_ids:
            logging.warning('Default session type ID not in available session types - will use the first one.')
            id_session_type = possible_session_types_ids[0]

        # Browse all data folders
        for (dir_path, dir_name, files) in os.walk(base_folder):
            if dir_path == base_folder:
                continue
            logging.info('WatchServerOpenTera: Processing ' + dir_path)
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
            log_file = os.path.join(dir_path, 'watch_logs.txt')
            log_file = log_file.replace('/', os.sep)
            if not os.path.isfile(log_file):
                logging.error('No watch logs file in ' + dir_path)
                continue

            with open(log_file) as f:
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

            # Clean session parameters
            session_params = session_data_json['description'].split('Settings:')[-1]
            session_params = session_params.replace('\n', '').replace('\t', '').replace(',,', ',').replace('{,', '{'). \
                replace(' ', '').replace(',}', '}')

            session_comments = 'Created by ' + device_name + ', v' + session_data_json['appVersion']

            # Create session
            if 'timestamp' in session_data_json:
                session_name = session_data_json['timestamp']
                session_starttime = datetime.datetime.fromisoformat(session_data_json['timestamp'].replace('_', ' ')).isoformat()
            else:
                logging.warning('No session timestamp found - using current time')
                session_name = device_name
                session_starttime = datetime.datetime.isoformat()

            session_info = {'id_session': 0, 'session_name': session_name, 'session_start_datetime': session_starttime,
                            'session_duration': int(duration), 'session_status': 2,  # Completed
                            'session_parameters': session_params, 'session_comments': session_comments,
                            'id_session_type': id_session_type}

            response = device_com.do_post(DeviceAPI.ENDPOINT_DEVICE_SESSIONS, {'session': session_info})
            if response.status_code != 200:
                logging.error('OpenTera: Unable to create session - skipping: ' + str(response.status_code) +
                              ' - ' + response.text.strip())
                continue

            # Create session events

            # Upload all files to FileTransfer service
