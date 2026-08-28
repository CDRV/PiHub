from libs.servers.WatchServerBase import WatchServerBase
from libs.servers.handlers.SFTPAppleWatchRequestHandler import SFTPAppleWatchRequestHandler
from libs.uploaders.SFTPUploader import SFTPUploader

from pathlib import Path

import logging
import os
import threading
import struct


class WatchServerSFTP(WatchServerBase):

    server = None
    file_syncher_timer = None

    def __init__(self, server_config: dict, sftp_config: dict):

        # Setup request handler
        request_handler = SFTPAppleWatchRequestHandler

        super().__init__(server_config=server_config, request_handler=request_handler)
        self.sftp_config = sftp_config

        self.synching_files = False

        # Set file synching after a few seconds without receiving any data
        # self.file_syncher_timer = threading.Timer(20, self.sync_files)

    def run(self):
        # Check if all files are on sync on the server (after the main server has started)
        self.file_syncher_timer = threading.Timer(1, self.sync_files, [False])
        self.file_syncher_timer.start()

        super().run()

    def sync_files(self, check_internet: bool = True):
        logging.info("WatchServerSFTP: Synchronizing files with server...")
        if self.synching_files:
            logging.info("*** WatchServerSFTP: Already synching files. Will wait for next time.")
            return

        self.synching_files = True
        # Build list of files to transfer
        base_folder = self.data_path + '/ToProcess/'
        base_folder = base_folder.replace('/', os.sep)
        files = []
        full_files = []
        file_folders = []
        for (dp, dn, f) in os.walk(base_folder):
            if f:
                dp = dp.replace('/', os.sep)
                logging.info('Processing: ' + str(dp))
                if self.send_logs_only:
                    # Filter list of files to keep only log files
                    folder_files = [file for file in f if file.lower().endswith("txt") or file.lower().endswith("oimi")]
                else:
                    if self.minimal_dataset_duration > 0:
                        # Filter dataset that are too small (<10 seconds)
                        if 'watch_logs.txt' in f:
                            import csv
                            try:
                                duration = 0
                                with open(os.path.join(dp, 'watch_logs.txt'), newline='') as csvfile:
                                    log_reader = csv.reader(csvfile, delimiter='\t')
                                    first_timestamp = None
                                    for row in log_reader:
                                        if len(row) == 0:
                                            continue
                                        if not first_timestamp:
                                            first_timestamp = row[0]
                                        last_timestamp = row[0]
                                try:
                                    duration = float(last_timestamp) - float(first_timestamp)
                                except ValueError:
                                    logging.info('Badly formatted log file - ignoring dataset...')
                                    self.move_folder(dp, dp.replace('ToProcess', 'Rejected'))
                                    continue  # ... with next dataset!
                                # Update duration from "battery" file, if present, since "watch_logs" duration can be under-evaluated
                                # if watch battery was depleted or a new day started
                                battery_file = os.path.join(dp, 'watch_Battery.data')
                                battery_file = battery_file.replace('/', os.sep)
                                if os.path.isfile(battery_file):
                                    with open(battery_file, mode='rb') as f:
                                        try:
                                            f.seek(-10, os.SEEK_END)
                                        except OSError as e:
                                            logging.info('Badly formatted battery file - ignoring dataset...')
                                            f.close()
                                            self.move_folder(dp, dp.replace('ToProcess', 'Rejected'))
                                            continue
                                        batt_data = f.read(8)  # Read the last timestamp of the file
                                        if len(batt_data) == 8:
                                            batt_last_timestamp = struct.unpack("<Q", batt_data)[0] / 1000
                                            if batt_last_timestamp and batt_last_timestamp > float(last_timestamp):
                                                duration = float(batt_last_timestamp) - float(first_timestamp)
                                if duration <= self.minimal_dataset_duration:
                                    # Must reject! Too short!
                                    self.move_files([os.path.join(dp, file) for file in f], 'Rejected')
                                    logging.info('Rejected folder ' + dp + ': dataset too small.')
                                    continue  # Move to next folder
                            except IOError:
                                pass  # Ignore error and move on!
                            except AssertionError:
                                pass

                    folder_files = f
                files.extend(folder_files)
                full_files.extend([os.path.join(dp, file) for file in folder_files])
                file_folder = dp.replace(base_folder, '')
                file_folders.extend(self.server_base_folder + "/" + file_folder.replace(os.sep, '/')
                                    for _ in folder_files)

        # Filter duplicates
        # full_files = list(set(full_files))

        if full_files:
            logging.info('WatchServerSFTP: About to sync files...')

            # Send files using sftp
            # Sending files
            success = SFTPUploader.sftp_send(sftp_config=self.sftp_config, files_to_transfer=full_files,
                                             files_directory_on_server=file_folders,
                                             file_transferred_callback=self.file_was_processed,
                                             check_internet=check_internet)

            # Set files as processed
            if success:
                self.move_processed_files()
            else:
                # Something occurred... Try again in 5 minutes
                self.file_syncher_timer = threading.Timer(300, self.sync_files)
                self.file_syncher_timer.start()

        # for file in full_files:
        #     WatchServer.file_was_processed(file)
        else:
            logging.info('WatchServerSFTP: No file to sync!')
        # Clean up empty folders
        self.remove_empty_folders(Path(base_folder).absolute())
        logging.info("WatchServerSFTP: Synchronization done.")
        self.synching_files = False

    def new_file_received(self, device_name: str, filename: str):
        # Start timer to batch transfer files in 20 seconds
        self.file_syncher_timer = threading.Timer(20, self.sync_files)
        self.file_syncher_timer.start()
