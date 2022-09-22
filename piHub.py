##################################################
# PiHub project main script
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
import time
import logging
import sys

from libs.config.ConfigManager import ConfigManager
from libs.servers.BedServer import BedServer
from libs.servers.WatchServer import WatchServer
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
    if not config_man.load_config('config/PiHub.json'):
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
        watch_server = WatchServer(server_config=config_man.watch_server_config,
                                   sftp_config=config_man.sftp_config)

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
