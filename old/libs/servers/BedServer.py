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

import threading
import os
import socket


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
        try:
            SFTPUploader.sftp_sync_last(sftp_config=self.sftp_config, local_base_path=str(full_path.absolute()),
                                        remote_base_path=self.server_base_folder, check_internet=False)
            # SFTPUploader.sftp_sync(sftp_config=self.sftp_config, local_base_path=str(full_path.absolute()),
            #                      remote_base_path=self.server_base_folder)
        except Exception as e:
            logging.error("Bedserver: Unable to synchronize files - " + str(e))
        logging.info("BedServer: Synchronization done.")

    def run(self):
        logging.info('BedServer starting...')

        # Check if all files are on sync on the server, do it on a thread so the logger still start
        thread_sync = threading.Thread(target=self.sync_files)
        thread_sync.start()

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

        # self.server.timeout = 10.0
        self.is_running = True
        logging.info("BedServer started on port " + str(self.port))
        try:
            self.server.serve_forever()

        finally:
            logging.info("BedServer stopped.")

    def stop(self):
        super().stop()

        if self.server:
            self.server.shutdown()
            self.server.server_close()


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
        filepath = self.data_path + '/local_only/' + str(greetings)
        try:
            makedirs(name=filepath, exist_ok=True)
        except OSError as exc:
            logging.error('Error creating ' + filepath + ': ' + exc.strerror)
            self.rfile.close()
            raise

        filename = filepath + "/" + str(datetime.now().date()) + ".txt"
        try:
            file = open(filename, 'a')
            file.write(str(datetime.now()) + "\t")
        except IOError as exc:
            logging.error('Error writing to file' + filename + ': ' + exc.strerror)
            self.rfile.close()
            raise

        # Loop to transfer data (2 bytes at a time - UINT16 are read from RAM and transmitted by ESP
        logging.info('Starting data transfer...')
        self.request.settimeout(10)
        while self.connection:
            try:
                d1minidata = self.request.recv(2)  # self.rfile.read(2)
                if len(d1minidata) == 0:
                    break
                else:
                    x = int.from_bytes(d1minidata, byteorder='little', signed=False)
                    file.write(str(x) + "\t")
            except (socket.timeout, TimeoutError, ConnectionResetError, ConnectionAbortedError, ConnectionError):
                logging.error("Timeout receiving data.")
                # self.request.settimeout(1.0)
                # while 1:
                #     try:
                #         self.request.recv(1)  # Clear all pending bytes, if available.
                #     except (TimeoutError, ConnectionResetError, ConnectionAbortedError, ConnectionError):
                #         break
                self.rfile.close()
                # logging.error("Remote stream closed")
                break
        logging.info("Data transfer complete.")
        file.write("\n")
        file.close()

        # Send file using SFTP
        file_server_directory = self.server_base_folder + "/" + str(greetings)
        file_server_path = file_server_directory + "/" + str(datetime.now().date()) + ".txt"
        temp_file = self.data_path + "/local_only/" + str(greetings) + "/tempData.txt"
        file_transferred_directory = self.data_path + "/transferred/" + str(greetings)
        logging.info("Try to create " + file_transferred_directory + ", dir exists = " +
                     str(not os.path.isdir(file_transferred_directory)))
        if not os.path.isdir(file_transferred_directory):
            makedirs(file_transferred_directory)
        file_transferred_location = file_transferred_directory + "/" + str(datetime.now().date()) + ".txt"
        # Start SFTP transfer in a new thread, so this one doesn't wait on the transfer
        # sftp = threading.Thread(target=SFTPUploader.sftp_send, args=(self.sftp_config, file_server_location,
        #                                                              filename))
        # sftp.start()

        # Add a file merge before transfer
        SFTPUploader.sftp_merge_and_send(sftp_config=self.sftp_config, file_path_on_server=file_server_path,
                                         file_server_location=file_server_directory, temporary_file=temp_file,
                                         file_transferred_location=file_transferred_location, file_to_transfer=filename)
