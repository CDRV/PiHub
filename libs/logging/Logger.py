##################################################
# PiHub logger
##################################################
# Author: Simon Brière, Eng. MASc.
##################################################
import logging

log_format = '[%(levelname)s]\t%(asctime)s\t%(threadName)s\t%(message)s'


def init_global_logger():
    logging.basicConfig(level=logging.DEBUG, format=log_format)
    # formatter = logging.Formatter('[%(levelname)s]\t%(asctime)s\t%(threadName)s\t%(message)s')


def init_file_logger(filepath: str):
    filename = filepath + '/logs.txt'  # "/log_" + datetime.now().strftime('%Y%m%d_%H%M%S') + '.txt'
    file_logger = logging.FileHandler(filename=filename)
    file_logger.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(file_logger)
