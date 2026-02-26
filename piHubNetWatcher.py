import time
import logging
import sys

from libs.hardware.PiHubHardware import PiHubHardware

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

    from libs.logging.Logger import init_file_logger

    init_file_logger("./logs/watcher")
    logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting up PiHubNetWatcher")
    try:
        # Main loop on main thread
        while True:
            # Watchdog
            # Wait to check again in a few minutes
            time.sleep(300)
            # Check if the USB dongle is still there
            if not PiHubHardware.has_usb_device('Qualcomm'):
                logging.warning('USB Dongle not detected - rebooting USB hub...')
                PiHubHardware.reboot_usb_hub()
                logging.info('Completed USB hub cycling.')

    except (KeyboardInterrupt, SystemExit):
        logging.info("PiHubNetWatcher stopped by user.")
        exit(0)
    logging.info("PiHubNetWatcher stopped.")