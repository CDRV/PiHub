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

    def __init__(self, server_config: dict, sftp_config: dict):
        super().__init__(server_config=server_config)
        self.sftp_config = sftp_config
        self.server_base_folder = server_config['server_base_folder']
        self.sftp_transfer = server_config['sftp_transfer']
        self.opentera_transfer = server_config['opentera_transfer']
        self.send_logs_only = server_config['send_logs_only']

    def run(self):
        logging.info('Apple Watch Server starting...')

        # Check if all files are on sync on the server
        self.sync_files()

        request_handler = AppleWatchRequestHandler
        request_handler.base_server = self

        self.server = ThreadingHTTPServer((self.hostname, self.port), request_handler)
        self.server.timeout = 5         # 5 seconds timeout should be ok since we are usually on local network
        self.is_running = True
        logging.info('Apple Watch Server started on port ' + str(self.port))

        self.server.serve_forever()
        self.server.server_close()

        logging.info("Apple Watch Server stopped.")

    def stop(self):
        super().stop()

        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def sync_files(self):
        logging.info("WatchServer: Synchronizing files with server...")
        # Build list of files to transfer
        base_folder = self.data_path + '/ToProcess/'
        files = []
        full_files = []
        file_folders = []
        for (dp, dn, f) in os.walk(base_folder):
            if f:
                if self.send_logs_only:
                    # Filter list of files to keep only log files
                    folder_files = [file for file in f if file.lower().endswith("txt") or file.lower().endswith("oimi")]
                else:
                    folder_files = f
                files.extend(folder_files)
                full_files.extend([os.path.join(dp.replace('/', os.sep), file) for file in folder_files])
                file_folder = dp.replace(base_folder, '')
                file_folders.extend("/" + self.server_base_folder + "/" + file_folder.replace(os.sep, '/')
                                    for _ in folder_files)

        # Filter duplicates
        # full_files = list(set(full_files))

        if files:
            logging.info('About to sync files...')

            if self.sftp_transfer:
                # Send files using sftp
                # Sending files
                SFTPUploader.sftp_send(sftp_config=self.sftp_config, files_to_transfer=full_files,
                                       files_path_on_server=file_folders)

            # Set files as processed
            # TODO: Provide a callback function that is called when the file is really transferred since, currently,
            #  SFTP transfers occurs in their own threads
            for file in full_files:
                WatchServer.file_was_processed(file)
        else:
            logging.info('No file to sync!')
        # Clean up empty folders
        WatchServer.remove_empty_folders(Path(base_folder).absolute())
        logging.info("WatchServer: Synchronization done.")

    @staticmethod
    def file_was_processed(full_filepath: str):
        # Move file to the "Processed" folder
        target_file = full_filepath.replace(os.sep + 'ToProcess' + os.sep, os.sep + 'Processed' + os.sep)

        # Create directory, if needed
        target_dir = os.path.dirname(target_file)
        try:
            os.makedirs(name=target_dir, exist_ok=True)
        except OSError as exc:
            logging.error('Error creating ' + target_dir + ': ' + exc.strerror)
            raise

        os.replace(full_filepath, target_file)
        # logging.info("Processed file: " + full_filepath)

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
            self.base_server.sync_files()
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
                content_received = (content_length - content_size_remaining)
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
            return

        # All is good!
        logging.info(device_name + " - " + file_name + ": transfer complete.")

        # # Need to transfer using SFTP?
        # if self.base_server.sftp_transfer:
        #
        #     # Check if we need to transfer only log files and if it's a log file
        #     if not self.base_server.send_logs_only or \
        #             (self.base_server.send_logs_only and file_type.lower() in ['txt', 'oimi']):
        #         file_name = Path(file_name).absolute()  # Get full path
        #         file_server_location = "/" + self.base_server.server_base_folder + "/" + device_name + "/" + file_path
        #         sftp = threading.Thread(target=SFTPUploader.sftp_send, args=(self.base_server.sftp_config,
        #                                                                      file_server_location, file_name))
        #         sftp.start()

        self.send_response(200)
        self.send_header('Content-type', 'file-transfer/ack')
        self.end_headers()

