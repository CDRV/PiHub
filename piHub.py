import time
import logging
import sys
import os

from libs.config.ConfigManager import ConfigManager
from libs.servers.BedServer import BedServer
from libs.servers.WatchServerSFTP import WatchServerSFTP
from libs.servers.WatchServerOpenTera import WatchServerOpenTera
from libs.servers.folderWatcher import FolderWatcher
from libs.hardware.PiHubHardware import PiHubHardware

from Globals import version_string


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

if __name__ == '__main__':
    # Logging module
    ################
    from libs.logging.Logger import init_global_logger

    init_global_logger()

    # Init globals
    ##############
    config_man = ConfigManager()

    # Load config file
    logging.info("Starting up PiHub v" + version_string + "...")
    config_file = 'config/PiHub_Defaults.json'
    if os.path.isfile('config/PiHub.json'):
        config_file = 'config/PiHub.json'
    else:
        logging.warning('No specific config file - using default config!')
    logging.info('Using config file: ' + config_file)
    if not config_man.load_config(config_file):
        logging.critical("Invalid config - system halted.")
        exit(1)

    # Set logger parameters
    if config_man.general_config["enable_logging"]:
        from libs.logging.Logger import init_file_logger

        init_file_logger(config_man.general_config["logs_path"])

    # Initializing...
    servers = []

    # Wait for Internet connection
    # PiHubHardware.wait_for_internet()

    # Bed Server
    if config_man.general_config["enable_bed_server"]:
        # Start bed server
        bed_server = BedServer(server_config=config_man.bed_server_config,
                               sftp_config=config_man.sftp_config)

        # Start server
        bed_server.start()
        servers.append(bed_server)

    # Apple Watch server
    if config_man.general_config["enable_watch_server"]:
        # Start Apple Watch server
        watch_server = None
        if config_man.watch_server_config['transfer_type'] == 'sftp':
            watch_server = WatchServerSFTP(server_config=config_man.watch_server_config,
                                           sftp_config=config_man.sftp_config)
        if config_man.watch_server_config['transfer_type'] == 'opentera':
            watch_server = WatchServerOpenTera(server_config=config_man.watch_server_config,
                                               opentera_config=config_man.opentera_config)
        if not watch_server:
            logging.critical('Unknown Watch Server Transfer type "' + config_man.watch_server_config['transfer_type']
                             + '" - will not start server')
        else:
            # Start server
            watch_server.start()
            servers.append(watch_server)

    # Folder Watcher server
    if config_man.general_config["enable_folderWatcher_server"]:
        # Start Apple Watch server
        folderWatcher_server = FolderWatcher(server_config=config_man.folderWatcher_server_config,
                                             sftp_config=config_man.sftp_config)

        # Start server
        folderWatcher_server.start()
        servers.append(folderWatcher_server)

    logging.info("PiHub " + version_string + " started.")

    try:
        # Main loop on main thread
        while True:
            # Watchdog
            # Wait to check again in a few minutes
            time.sleep(600)
            # Check if we have Internet access or not
            PiHubHardware.ensure_internet_is_available()

    except (KeyboardInterrupt, SystemExit):
        for server in servers:
            server.stop()
        logging.info("PiHub stopped by user.")
        exit(0)
    logging.info("PiHub stopped.")
