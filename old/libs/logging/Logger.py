##################################################
# PiHub logger
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import logging
import os
from logging.handlers import TimedRotatingFileHandler

log_format = '[%(levelname)s]\t%(asctime)s\t%(threadName)s\t%(message)s'


def init_global_logger():
    logging.basicConfig(level=logging.INFO, format=log_format)
    # formatter = logging.Formatter('[%(levelname)s]\t%(asctime)s\t%(threadName)s\t%(message)s')


def init_file_logger(filepath: str):
    try:
        os.makedirs(name=filepath, exist_ok=True)
    except OSError as exc:
        logging.error('Error creating ' + filepath + ': ' + exc.strerror)
        raise

    filename = filepath + '/logs.txt'  # "/log_" + datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt'
    file_logger = TimedRotatingFileHandler(filename=filename, when='d')
    file_logger.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(file_logger)
