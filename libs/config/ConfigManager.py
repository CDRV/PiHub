##################################################
# PiHub config file manager
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################

import json


class ConfigManager:

    def __init__(self):
        self.server_config = {}
        self.sftp_config = {}
        self.opentera_config = {}

    def load_config(self, filename):
        from Globals import logger

        try:
            config_file = open(filename, mode='rt', encoding='utf8')
            config_json = json.load(config_file)
            config_file.close()
        except IOError as e:
            logger.log_error("Error loading file: " + filename + " - " + str(e))
            return
        except json.JSONDecodeError as e:
            logger.log_error("Error decoding file: " + filename + " - " + str(e))
            return

        if self.validate_server_config(config_json['Server']):
            self.server_config = config_json["Server"]

        if self.validate_sftp_config(config_json['SFTP']):
            self.sftp_config = config_json["SFTP"]

        if self.validate_opentera_config(config_json['OpenTera']):
            self.opentera_config = config_json["OpenTera"]

    @staticmethod
    def validate_server_config(config):
        from Globals import logger
        rval = True

        required_fields = ['hostname', 'port', 'enable_sftp', 'enable_opentera', 'enable_logging', 'data_path']
        for field in required_fields:
            if field not in config:
                logger.log_error('Server Config - missing "' + field + '"')
                rval = False

        return rval

    @staticmethod
    def validate_sftp_config(config):
        from Globals import logger
        rval = True
        required_fields = ['hostname', 'port', 'username', 'password']
        for field in required_fields:
            if field not in config:
                logger.log_error('SFTP Config - missing "' + field + '"')
                rval = False
        return rval

    @staticmethod
    def validate_opentera_config(config):
        from Globals import logger
        rval = True
        required_fields = ['hostname', 'port']
        for field in required_fields:
            if field not in config:
                logger.log_error('OpenTera Config - missing "' + field + '"')
                rval = False
        return rval
