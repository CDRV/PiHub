##################################################
# PiHub project main script
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
import time
import logging

from libs.config.ConfigManager import ConfigManager
from libs.servers.BedServer import BedServer
from libs.utils.Network import Network
from libs.hardware.PiHubHardware import PiHubHardware

if __name__ == '__main__':
    # Logging module
    ################
    from libs.logging.Logger import init_global_logger
    init_global_logger()

    # Init globals
    ##############
    config_man = ConfigManager()

    # Load config file
    logging.info("Starting up PiHub...")
    if not config_man.load_config('config/PiHub.json'):
        logging.critical("Invalid config - system halted.")
        exit(1)

    # Set logger parameters
    if config_man.general_config["enable_logging"]:
        from libs.logging.Logger import init_file_logger
        init_file_logger(config_man.general_config["logs_path"])

    # Initializing...
    servers = []

    if config_man.general_config["enable_bed_server"]:
        # Start bed server
        bed_server = BedServer(server_config=config_man.bed_server_config,
                               sftp_config=config_man.sftp_config)
        bed_server.start()
        servers.append(bed_server)

    logging.info("PiHub started.")
    try:
        # Main loop on main thread
        while True:
            # Watchdog
            # Check if we have Internet access or not
            logging.debug('Watchdog - checking Internet connection')
            if not Network.is_internet_connected():
                logging.warning('Internet is down... Trying to reboot cellular card.')
                # No internet connection... Try to reboot the cellular network
                PiHubHardware.reset_cellular_network()
                time.sleep(5)  # Wait 5 seconds to see if network is coming back online or not
                if not Network.is_internet_connected():
                    logging.warning('Reboot completed, but still no Internet... Rebooting...')
                    # Still no internet connection - reboot the pi!
                    PiHubHardware.reboot()
                logging.info('Internet is back. All is fine.')
            # Wait to check again in a few seconds
            time.sleep(120)
            
    except (KeyboardInterrupt, SystemExit):
        for server in servers:
            server.stop()
        logging.info("PiHub stopped by user.")
        exit(0)
    logging.info("PiHub stopped.")

