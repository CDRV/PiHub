from libs.servers.WatchServerBase import WatchServerBase
from libs.servers.handlers.SFTPAppleWatchRequestHandler import SFTPAppleWatchRequestHandler
from libs.uploaders.SFTPUploader import SFTPUploader

from pathlib import Path

import logging
import os
import threading


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
                if self.send_logs_only:
                    # Filter list of files to keep only log files
                    folder_files = [file for file in f if file.lower().endswith("txt") or file.lower().endswith("oimi")]
                else:
                    if self.minimal_dataset_duration > 0:
                        # Filter dataset that are too small (<10 seconds)
                        if 'watch_logs.txt' in f:
                            import csv
                            try:
                                with open(os.path.join(dp, 'watch_logs.txt'), newline='') as csvfile:
                                    log_reader = csv.reader(csvfile, delimiter='\t')
                                    first_timestamp = None
                                    for row in log_reader:
                                        if len(row) == 0:
                                            continue
                                        if not first_timestamp:
                                            first_timestamp = row[0]
                                        last_timestamp = row[0]
                                duration = float(last_timestamp) - float(first_timestamp)
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
