from http.server import BaseHTTPRequestHandler
from pathlib import Path

import logging
import os


class BaseAppleWatchRequestHandler(BaseHTTPRequestHandler):
    base_server = None

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
            self.base_server.device_disconnected(self.headers['Device-Name'])
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

        # Signal base server that we got new files
        if self.base_server:
            self.base_server.new_file_received(device_name, file_name)
