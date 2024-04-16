from libs.servers.WatchServerBase import WatchServerBase
from libs.servers.handlers.OpenTeraAppleWatchRequestHandler import OpenTeraAppleWatchRequestHandler

from opentera_libraries.device.DeviceComManager import DeviceComManager
from opentera_libraries.common.Constants import SessionStatus, SessionEventTypes, SessionCategoryEnum

import opentera_libraries.device.DeviceAPI as DeviceAPI
from cryptography.fernet import Fernet
from threading import Lock

import logging
import os
import threading
import json
import datetime

opentera_lock = Lock()


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
        if os.path.isdir(base_folder):
            for device_name in os.listdir(base_folder):
                self.initiate_opentera_transfer(device_name)

        logging.info("All done!")

    def initiate_opentera_transfer(self, device_name: str):
        # Only one thread can transfer at a time - this prevent file conflicts
        with opentera_lock:
            logging.info("WatchServerOpenTera: Initiating data transfer for " + device_name + "...")

            if device_name in self._device_timeouts:
                # Stop timer if needed
                self._device_timeouts[device_name].cancel()

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
                                          if st['session_type_category'] == SessionCategoryEnum.DATACOLLECT.value]
            if len(possible_session_types_ids) == 0:
                logging.error('No "Data Collect" session types available to this device - will not transfer until this '
                              'is fixed.')
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

                session_comments = 'Created by ' + device_name + ', SensorLogger v' + session_data_json['appVersion']

                # Create session
                if 'timestamp' in session_data_json:
                    session_starttime = datetime.datetime.fromisoformat(session_data_json['timestamp'].replace('_', ' '))
                else:
                    logging.warning('No session timestamp found - using current time')
                    session_starttime = datetime.datetime.now()

                session_name = device_name + ' (PiHub) ' + session_starttime.strftime("%Y-%m-%d")

                session_info = {'id_session': 0, 'session_name': session_name,
                                'session_start_datetime': session_starttime.isoformat(),
                                'session_duration': int(duration), 'session_status': SessionStatus.STATUS_COMPLETED.value,
                                'session_parameters': session_params, 'session_comments': session_comments,
                                'id_session_type': id_session_type,
                                'session_participants': [part['participant_uuid'] for part in participants_infos]}

                response = device_com.do_post(DeviceAPI.ENDPOINT_DEVICE_SESSIONS, {'session': session_info})
                if response.status_code != 200:
                    logging.error('OpenTera: Unable to create session - skipping: ' + str(response.status_code) +
                                  ' - ' + response.text.strip())
                    continue

                id_session = response.json()['id_session']

                # Create session events
                session_events = self.watch_logs_to_events(logs_data)
                for event in session_events:
                    event['id_session'] = id_session
                    event['id_session_event'] = 0
                    response = device_com.do_post(DeviceAPI.ENDPOINT_DEVICE_SESSION_EVENTS, {'session_event': event})
                    if response.status_code != 200:
                        logging.error('OpenTera: Unable to create session event - skipping: ' + str(response.status_code) +
                                      ' - ' + response.text.strip())
                        continue

                # Upload all files to FileTransfer service
                for data_file in files:
                    full_path = str(os.path.join(dir_path, data_file))
                    logging.info('Uploading ' + full_path + '...')
                    response = device_com.upload_file(id_session=id_session, asset_name=data_file, file_path=full_path)
                    if response.status_code != 200:
                        logging.error('OpenTera: Unable to upload file - skipping: ' + str(response.status_code) +
                                      ' - ' + response.text.strip())
                        continue

                logging.info('WatchServerOpenTera: Done processing ' + dir_path)
                self.processed_files.append(dir_path)

                # All done for that folder - move to processed folder after a small delay to allow uploaded files to
                # properly close
                # threading.Timer(interval=1, function=self.move_folder,
                #                 kwargs={'source_folder': dir_path,
                #                         'target_folder': dir_path.replace('ToProcess', 'Processed')}).start()

            for dir_path in self.processed_files:
                logging.info('Moving ' + dir_path + '...')
                self.move_folder(dir_path, dir_path.replace('ToProcess', 'Processed'))
            self.processed_files.clear()
            logging.info('WatchServerOpenTera: Data transfer for ' + device_name + ' completed')

    @staticmethod
    def watch_logs_to_events(logs: list) -> list:
        # Parse the watch logs to TeraSession events - {event_type, event_datetime, event_text, event_context}

        # Create mapping between logger event and TeraSessionEvents
        events_map = {
            0: SessionEventTypes.GENERAL_ERROR.value,
            1: SessionEventTypes.GENERAL_INFO.value,
            2: SessionEventTypes.GENERAL_WARNING.value,
            3: SessionEventTypes.SESSION_START.value,
            4: SessionEventTypes.SESSION_STOP.value,
            5: SessionEventTypes.DEVICE_ON_CHARGE.value,
            6: SessionEventTypes.DEVICE_OFF_CHARGE.value,
            7: SessionEventTypes.DEVICE_LOW_BATT.value,
            8: SessionEventTypes.DEVICE_STORAGE_LOW.value,
            9: SessionEventTypes.DEVICE_STORAGE_FULL.value,
            10: SessionEventTypes.DEVICE_EVENT.value,
            11: SessionEventTypes.USER_EVENT.value
        }

        # Process the logs
        events = []
        for log in logs:
            log_data = log.split('\t')
            # 0 = UNIX Timestamp, 1 = EventType, 2 = Context, 3 = Time string, 4 = Text
            if len(log_data) != 5:
                logging.warning('Watch Log entry is not in a known format - ignoring.')
                continue

            log_time = datetime.datetime.fromtimestamp(float(log_data[0]))
            if int(log_data[1]) in events_map:
                log_type = events_map[int(log_data[1])]
            else:
                logging.warning('Watch log event type ' + log_data[1] + ' not directly mapped to a '
                                                                        'TeraSessionEvent - using DeviceEvent.')
                log_type = SessionEventTypes.DEVICE_EVENT.value
            session_event = {
                'id_session_event_type': log_type,
                'session_event_datetime': log_time.isoformat(),
                'session_event_text': log_data[4],
                'session_event_context': log_data[2]
            }
            events.append(session_event)

        return events