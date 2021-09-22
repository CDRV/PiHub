##################################################
# PiHub logger
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################

import json
import time
from os import makedirs
from datetime import datetime


class Logger:

    def __init__(self):
        self.log_path = None   # By default, don't log into files since we don't have a path yet
        self.current_log_file = None

    def set_log_path(self, log_path):
        if log_path is None:
            self.log_path = None
            self.current_log_file = None
            return

        # Create path if doesn't exists
        try:
            makedirs(name=log_path, exist_ok=True)
        except OSError as exc:
            print('Error creating ' + log_path + ': ' + exc.strerror)
            raise

        # Set path
        self.log_path = log_path

        # Set current log file
        self.update_current_log_file()

    def update_current_log_file(self):
        self.current_log_file = self.log_path + "/logs.txt"
        # "/log_" + datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt'

    def __save_log(self, prefix: str, log: str):

        # + str(time.mktime(datetime.now().timetuple())) + '\t' + \
        log_str = '[' + prefix + ']\t' + \
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + '\t' + log

        print(log_str)
        if self.current_log_file:
            error_file = open(self.current_log_file, 'a+')
            error_file.write(log_str + '\n')
            error_file.close()

    def log_info(self, log: str):
        self.__save_log('INFO', log)

    def log_error(self, log: str):
        self.__save_log('ERROR', log)

    def log_warning(self, log: str):
        self.__save_log('WARNING', log)
