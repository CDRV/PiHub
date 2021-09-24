##################################################
# PiHub main bed communication server
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
from libs.servers.BaseServer import BaseServer
from libs.uploaders.SFTPUploader import SFTPUploader

import logging
import socketserver
from os import makedirs
from datetime import datetime
from pathlib import Path


class BedServer(BaseServer):

    server = None

    def __init__(self, server_config: dict, sftp_config: dict):
        super().__init__(server_config=server_config)
        self.sftp_config = sftp_config
        self.server_base_folder = server_config['server_base_folder']

    def sync_files(self):
        logging.info("BedServer: Synchronizing files with server...")
        full_path = Path(self.data_path)

        # Sync local files with the ones on the server
        SFTPUploader.sftp_sync(sftp_config=self.sftp_config, local_base_path=str(full_path.absolute()),
                               remote_base_path=self.server_base_folder)
        logging.info("BedServer: Synchronization done.")

    def run(self):
        logging.info('BedServer starting...')

        # Check if all files are on sync on the server
        self.sync_files()

        try:
            # Add custom values that are need in the request handler
            request_handler = BedServerRequestHandler
            request_handler.sftp_config = self.sftp_config
            request_handler.data_path = self.data_path
            request_handler.server_base_folder = self.server_base_folder

            self.server = socketserver.ThreadingTCPServer(server_address=(self.hostname, self.port),
                                                          RequestHandlerClass=request_handler)

        except OSError as e:
            logging.critical(e.strerror)
            return
        except OverflowError as e:
            logging.critical(str(e))
            return

        self.server.timeout = 10.0
        self.is_running = True
        logging.info("BedServer started.")
        try:
            self.server.serve_forever()

        finally:
            logging.info("BedServer stopped.")

    def stop(self):
        super().stop()

        if self.server:
            self.server.shutdown()


class BedServerRequestHandler(socketserver.StreamRequestHandler):

    data_path: str = None
    sftp_config: dict = None
    server_base_folder: str = None

    def handle(self) -> None:
        # Greet device
        logging.info('Got connection from: ' + self.client_address[0])
        greetings = self.request.recv(22)
        # greetings = self.rfile.read(1).strip()
        greetings = greetings.decode('utf-8')
        logging.info('Device identified as: ' + greetings)

        # Establish the correct filename (will be updated each time the sensor is connected
        # Will append the file or create a new one if non-existing
        # filename = Path("/home/pi/Desktop/Data/"+str(datetime.datetime.now().date())+".txt")
        filepath = self.data_path + '/' + str(greetings)
        try:
            makedirs(name=filepath, exist_ok=True)
        except OSError as exc:
            logging.error('Error creating ' + filepath + ': ' + exc.strerror)
            self.rfile.close()
            raise

        filename = filepath + "/" + str(datetime.now().date())+".txt"
        try:
            file = open(filename, 'a')
            file.write(str(datetime.now()) + "\t")
        except IOError as exc:
            logging.error('Error writing to file' + filename + ': ' + exc.strerror)
            self.rfile.close()
            raise

        # Loop to transfer data (4 bytes at a time - UINT32 are read from RAM and transmitted by ESP
        logging.info('Starting data transfer...')
        while self.connection:
            try:
                d1minidata = self.request.recv(4)  # self.rfile.read(4)
                if len(d1minidata) == 0:
                    break
                else:
                    x = int.from_bytes(d1minidata, byteorder='little', signed=False)
                    file.write(str(x)+"\t")
            except TimeoutError as e:
                self.rfile.close()
                logging.error("Timeout receiving data.")
                break
        logging.info("Data transfer complete.")
        file.write("\n")
        file.close()

        # Send file using SFTP
        file_server_location = "/" + self.server_base_folder + "/" + str(greetings)
        # Start SFTP transfer in a new thread, so this one doesn't wait on the transfer
        # sftp = threading.Thread(target=SFTPUploader.sftp_send, args=(self.sftp_config, file_server_location,
        #                                                              filename))
        # sftp.start()

        SFTPUploader.sftp_send(self.sftp_config, file_server_location, filename)
