##################################################
# PiHub Apple Watch communication server
##################################################
# Authors: Simon Brière, Eng. MASc.
##################################################
from libs.servers.BaseServer import BaseServer
from libs.uploaders.SFTPUploader import SFTPUploader

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import logging
import os
import threading


class WatchServer(BaseServer):

    server = None
    processed_files = []

    def __init__(self, server_config: dict, sftp_config: dict):
        super().__init__(server_config=server_config)
        self.sftp_config = sftp_config
        self.server_base_folder = server_config['server_base_folder']
        self.sftp_transfer = server_config['sftp_transfer']
        self.opentera_transfer = server_config['opentera_transfer']
        self.send_logs_only = server_config['send_logs_only']
        self.minimal_dataset_duration = server_config['minimal_dataset_duration']

        self.synching_files = False

        # Set file synching after a few seconds without receiving any data
        self.file_syncher_timer = threading.Timer(20, self.sync_files)

    def run(self):
        logging.info('Apple Watch Server starting...')

        # Check if all files are on sync on the server
        # self.sync_files(check_internet=False)  # Don't explicitely check internet connection on startup

        request_handler = AppleWatchRequestHandler
        request_handler.base_server = self

        self.server = ThreadingHTTPServer((self.hostname, self.port), request_handler)
        self.server.timeout = 5         # 5 seconds timeout should be ok since we are usually on local network
        self.is_running = True
        logging.info('Apple Watch Server started on port ' + str(self.port))

        # Check if all files are on sync on the server (after the main server has started)
        self.file_syncher_timer = threading.Timer(1, self.sync_files, [False])
        self.file_syncher_timer.start()

        # Thread will wait here
        self.server.serve_forever()
        self.server.server_close()

        logging.info("Apple Watch Server stopped.")

    def stop(self):
        super().stop()

        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def sync_files(self, check_internet: bool = True):
        logging.info("WatchServer: Synchronizing files with server...")
        if self.synching_files:
            logging.info("*** WatchServer: Already synching files. Will wait for next time.")
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
            logging.info('About to sync files...')

            if self.sftp_transfer:
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
            logging.info('No file to sync!')
        # Clean up empty folders
        WatchServer.remove_empty_folders(Path(base_folder).absolute())
        logging.info("WatchServer: Synchronization done.")
        self.synching_files = False

    def file_was_processed(self, full_filepath: str):
        # Mark file as processed - will be moved later on to prevent conflicts
        self.processed_files.append(full_filepath)

    def move_files(self, source_files, target_folder):
        for full_filepath in source_files:
            # Move file from "ToProcess" to the target folder
            target_file = full_filepath.replace(os.sep + 'ToProcess' + os.sep, os.sep + target_folder + os.sep)

            # Create directory, if needed
            target_dir = os.path.dirname(target_file)
            try:
                os.makedirs(name=target_dir, exist_ok=True)
            except OSError as exc:
                logging.error('Error creating ' + target_dir + ': ' + exc.strerror)
                continue
                # raise

            try:
                os.rename(full_filepath, target_file)
            except (OSError, IOError) as exc:
                logging.error('Error moving ' + full_filepath + ' to ' + target_file + ': ' + exc.strerror)
                continue
                # raise

    def move_processed_files(self):
        self.move_files(self.processed_files, 'Processed')
        self.processed_files.clear()

    @staticmethod
    def remove_empty_folders(path_abs):
        walk = list(os.walk(path_abs))
        for path, _, _ in walk[::-1]:
            if len(os.listdir(path)) == 0:
                os.rmdir(path.replace("/", os.sep))


class AppleWatchRequestHandler(BaseHTTPRequestHandler):

    base_server: WatchServer = None

    def setup(self):
        BaseHTTPRequestHandler.setup(self)

    # Simple get to show what to do for file transfer
    def do_GET(self):

        # Ping requests can be answered directly
        content_type = self.headers['Content-Type']
        if content_type == 'cdrv-cmd/Connect':
            # self.streamer.add_log.emit("Connexion de " + self.headers['Device-Name'], LogTypes.LOGTYPE_INFO)
            logging.info(self.headers['Device-Name'] + ' connected.')
            self.send_response(202)
            self.send_header('Content-type', 'cdrv-cmd/Connect')
            self.end_headers()
            return

        if content_type == 'cdrv-cmd/Disconnect':
            # self.streamer.add_log.emit("Déconnexion de " + self.headers['Device-Name'], LogTypes.LOGTYPE_INFO)
            logging.info(self.headers['Device-Name'] + ' disconnected.')
            self.send_response(202)
            self.send_header('Content-type', 'cdrv-cmd/Disconnect')
            self.end_headers()
            # self.base_server.sync_files()
            return

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):

        # Unpack metadata
        content_type = self.headers['Content-Type']
        content_length = int(self.headers['Content-Length'])
        file_type = self.headers['File-Type']
        device_type = self.headers['Device-Type']
        device_name = self.headers['Device-Name']
        file_path = self.headers['File-Path']
        file_name = self.headers['File-Name']

        if None in [file_type, device_type, device_name, file_path, file_name]:
            logging.error(device_name + " - Badly formatted request - missing some headers.")
            self.send_response(400)
            self.end_headers()
            return

        if content_type != 'cdrv-cmd/File-Upload':
            logging.warning(device_name + " - Unknown command: " + content_type)
            self.send_response(400)
            self.end_headers()
            return

        # Stop timer to send data, since we received new data
        if self.base_server.file_syncher_timer and self.base_server.file_syncher_timer.is_alive():
            self.base_server.file_syncher_timer.cancel()
            self.base_server.file_syncher_timer = None

        # Prepare to receive data
        destination_dir = (self.base_server.data_path + '/ToProcess/' + device_name + '/' + file_path + '/')\
            .replace('//', '/').replace('/', os.sep)
        destination_path = destination_dir + file_name

        file_name = device_name + file_path + '/' + file_name
        logging.info(device_name + " - Receiving: " + file_name + " (" + str(content_length) + " bytes)")

        # Check if file exists and size matches
        file_infos = Path(destination_path)
        if file_infos.exists():
            file_infos = os.stat(destination_path)
            if file_infos.st_size < content_length:
                logging.warning(device_name + ": " + file_name + " - Existing file, but incomplete (" +
                                str(file_infos.st_size) + "/" + str(content_length) + " bytes), resending.")
            else:
                logging.warning(device_name + ": " + file_name + " - Existing file - replacing file.")

        # Destination directory if it doesn't exist
        Path(destination_dir).mkdir(parents=True, exist_ok=True)

        # Gets the data and save to file
        buffer_size = 4 * 1024
        content_size_remaining = content_length
        # last_pc = -1

        # Supported file type?
        if file_type.lower() in ['data', 'dat', 'csv', 'txt', 'oimi']:

            if file_type.lower() in ['data', 'dat']:
                # Binary file
                fh = open(destination_path, 'wb')
                text_format = False
            else:
                # Text file
                fh = open(destination_path, 'w')
                text_format = True

            while content_size_remaining > 0:
                if buffer_size > content_size_remaining:
                    buffer_size = content_size_remaining
                try:
                    data = self.rfile.read(buffer_size)
                except OSError as err:
                    err_desc = err.strerror
                    if not err_desc and len(err.args) > 0:
                        err_desc = err.args[0]
                    logging.error(device_name + " - Error occured while transferring " + file_name + ": " +
                                  str(err_desc))
                    return

                if text_format:
                    fh.write(data.decode())
                else:
                    fh.write(data)
                content_size_remaining -= buffer_size
                # content_received = (content_length - content_size_remaining)
                # pc = math.floor((content_received / content_length) * 100)
                # if pc != last_pc:
                #     self.streamer.update_progress.emit(file_name, " (" + str(content_received) + "/ " +
                #                                        str(content_length) + ")", (content_length -
                #                                                                    content_size_remaining),
                #                                        content_length)
                #     last_pc = pc
            fh.close()
        else:
            # self.streamer.add_log.emit(device_name + ": " + file_name + " - Type de fichier non-supporté: " +
            #                            file_type.lower(), LogTypes.LOGTYPE_ERROR)
            logging.error(device_name + " - " + file_name + " - Unsupported file type: " + file_type.lower())
            self.send_response(400)
            self.send_header('Content-type', 'file-transfer/invalid-file-type')
            self.end_headers()
            return

        # Check if everything was received correctly
        file_infos = os.stat(destination_path)
        if file_infos.st_size < content_length:
            # Missing data?!?!
            error = "Transfer error: " + str(file_infos.st_size) + " bytes received, " + str(content_length) + \
                    " expected."
            logging.error(device_name + " - " + file_name + " - " + error)
            self.send_response(400)
            self.send_header('Content-type', 'file-transfer/error')
            self.end_headers()
            return

        if content_length == 0 or (file_infos.st_size == 0 and content_length != 0):
            error = "Transfer error: 0 byte received."
            logging.error(device_name + " - " + file_name + " - " + error)
            self.send_response(400)
            self.send_header('Content-type', 'file-transfer/error')
            self.end_headers()
            return

        # All is good!
        logging.info(device_name + " - " + file_name + ": transfer complete.")

        self.send_response(200)
        self.send_header('Content-type', 'file-transfer/ack')
        self.end_headers()

        # Start timer to sync data, if no other transfer occurs until timeout
        self.base_server.file_syncher_timer = threading.Timer(20, self.base_server.sync_files)
        self.base_server.file_syncher_timer.start()

