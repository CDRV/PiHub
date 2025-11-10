##################################################
# PiHub config file manager
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################

import json
import logging
import os
from jsonmerge import merge


class ConfigManager:

    def __init__(self):
        self.general_config = {}
        self.sftp_config = {}
        self.opentera_config = {}
        self.bed_server_config = {}
        self.watch_server_config = {}
        self.folderWatcher_server_config = {}

    def load_config(self, filename, default_filename) -> bool:
        try:
            default_config_file = open(default_filename, mode='rt', encoding='utf8')
            default_config_json = json.load(default_config_file)
            default_config_file.close()
        except IOError as e:
            logging.error("Error loading file: " + filename + " - " + str(e))
            return False
        except json.JSONDecodeError as e:
            logging.error("Error decoding file: " + filename + " - " + str(e))
            return False

        config_json = {}
        if os.path.isfile(filename):
            logging.info('Using config file: ' + filename)
            try:
                config_file = open(filename, mode='rt', encoding='utf8')
                config_json = json.load(config_file)
                config_file.close()
            except IOError as e:
                logging.error("Error loading file: " + filename + " - " + str(e))
                return False
            except json.JSONDecodeError as e:
                logging.error("Error decoding file: " + filename + " - " + str(e))
                return False
        else:
            logging.warning('No specific config file - using default config: ' + default_filename)

        # Merge the 2 configs
        config_json = merge(default_config_json, config_json)

        if self.validate_config("General", config_json['General'], ['enable_bed_server', 'enable_watch_server',
                                                                    'enable_logging']):
            self.general_config = config_json["General"]

        if self.validate_config("SFTP", config_json['SFTP'], ['hostname', 'port', 'username', 'password']):
            self.sftp_config = config_json["SFTP"]

        if self.validate_config("OpenTera", config_json['OpenTera'],
                                ['hostname', 'port', 'device_register_key', 'default_session_type_id']):
            self.opentera_config = config_json["OpenTera"]

        if self.validate_config("WatchServer", config_json['WatchServer'], ['hostname', 'port', 'data_path',
                                                                            'transfer_type', 'server_base_folder',
                                                                            'send_logs_only', 'minimal_dataset_duration'
                                                                            ]):
            self.watch_server_config = config_json["WatchServer"]

        if self.validate_config("BedServer", config_json['BedServer'], ['hostname', 'port', 'data_path',
                                                                        'server_base_folder']):
            self.bed_server_config = config_json["BedServer"]

        if self.validate_config("FolderWatcher", config_json['FolderWatcher'], ['data_path',
                                                                                'server_base_folder', 'sensor_ID']):
            self.folderWatcher_server_config = config_json["FolderWatcher"]

        return True

    @staticmethod
    def validate_config(section: str, config: dict, required_fields: list):
        rval = True

        for field in required_fields:
            if field not in config:
                logging.error(section + ' Config - missing "' + field + '"')
                rval = False

        return rval
