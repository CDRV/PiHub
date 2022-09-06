##################################################
# PiHub main folder Watcher communication server
##################################################
# Authors: Antoine Guillerand
##################################################
from libs.servers.BaseServer import BaseServer
from libs.uploaders.SFTPUploader import SFTPUploader

import logging
from os import makedirs
from pathlib import Path

import threading
import os
import time


class FolderWatcher(BaseServer):
    server = None

    def __init__(self, server_config: dict, sftp_config: dict):
        super().__init__(server_config=server_config)
        self.sftp_config = sftp_config
        self.server_base_folder = server_config['server_base_folder']
        self.sensor_ID = server_config['sensor_ID']

    def sync_files(self):
        logging.info("FolderWatcher: Synchronizing files with server...")
        full_path = Path(self.data_path)

        # Sync local files with the ones on the server
        try:
            SFTPUploader.sftp_sync_last(sftp_config=self.sftp_config, local_base_path=str(full_path.absolute()),
                                        remote_base_path=self.server_base_folder, check_internet=False)
            # SFTPUploader.sftp_sync(sftp_config=self.sftp_config, local_base_path=str(full_path.absolute()),
            #                      remote_base_path=self.server_base_folder)
        except Exception as e:
            logging.error("FolderWatcher: Unable to synchronize files - " + str(e))
        logging.info("FolderWatcher: Synchronization done.")

    def run(self):
        logging.info('folderWatcher starting...')
        path_to_watch = self.data_path + '/local_only/' + self.sensor_ID
        logging.info("FolderWatcher: Path to watch: " + path_to_watch)
        # Check if all files are on sync on the server, do it on a thread so the logger still start
        if os.path.isdir(path_to_watch):
            thread_sync = threading.Thread(target=self.sync_files)
            thread_sync.start()
        else:
            logging.info("FolderWatcher: No Data Folder to sync at start")
            os.makedirs(path_to_watch)
        before = dict([(f, None) for f in os.listdir(path_to_watch)])

        logging.info("folderWatcher started")
        try:
            # Watch the filepath every 1s and if number of file changes transfer files.
            while 1:
                time.sleep(1)
                # Add this because we remove the folder if everything is transferred:
                if not (os.path.isdir(path_to_watch)):
                    os.makedirs(path_to_watch)
                after = dict([(f, None) for f in os.listdir(path_to_watch)])
                added = [f for f in after if not f in before]
                removed = [f for f in before if not f in after]
                # Check if a file was added or removed
                if added:
                    logging.info("FolderWatcher: Local File(s) Added: " + ", ".join(added))
                    for i in range(0, len(added)):
                        filename = self.data_path + '/local_only/' + self.sensor_ID + "/" + added[i]
                        # Send file using SFTP
                        file_server_directory = "/" + self.server_base_folder + "/" + self.sensor_ID
                        file_server_path = file_server_directory + "/" + added[i]  #
                        temp_file = self.data_path + "/local_only/" + self.sensor_ID + "/tempData.txt"
                        file_transferred_directory = self.data_path + "/transferred/" + self.sensor_ID
                        logging.info("Try to create " + file_transferred_directory + ", dir exists = " +
                                     str(not os.path.isdir(file_transferred_directory)))
                        if not os.path.isdir(file_transferred_directory):
                            makedirs(file_transferred_directory)
                        file_transferred_location = file_transferred_directory + "/" + added[i]
                        # Add a file merge before transfer
                        SFTPUploader.sftp_merge_and_send(sftp_config=self.sftp_config,
                                                         file_path_on_server=file_server_path,
                                                         file_server_location=file_server_directory,
                                                         temporary_file=temp_file,
                                                         file_transferred_location=file_transferred_location,
                                                         file_to_transfer=filename,
                                                         check_internet=False)
                if removed:
                    logging.info("FolderWatcher: Local file(s) Removed: " + ", ".join(removed))
                before = after

        except OSError as e:
            logging.critical(e.strerror)
            return
        except OverflowError as e:
            logging.critical(str(e))
            return

        finally:
            logging.info("folderWatcher stopped.")