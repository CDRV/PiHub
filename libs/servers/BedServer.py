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
import threading


class BedServer(BaseServer):

    server = None

    def __init__(self, server_config: dict, sftp_config: dict):
        super().__init__(server_config=server_config)
        self.sftp_config = sftp_config

    def run(self):
        logging.info('BedServer starting...')
        try:
            self.server = socketserver.ThreadingTCPServer(server_address=(self.hostname, self.port),
                                                          RequestHandlerClass=BedServerRequestHandler)

            # Add custom values that are need in the request handler
            self.server.sftp_config = self.sftp_config
            self.server.data_path = self.data_path
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
        filepath = self.server.data_path + '/' + str(greetings)
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
        logging.info("Data received! \n")
        file.write("\n")
        file.close()

        # Send file using SFTP
        file_server_location = "/Test/" + str(greetings)
        # Start SFTP transfer in a new thread, so this one doesn't wait on the transfer
        sftp = threading.Thread(target=SFTPUploader.sftp_send, args=(self.server.sftp_config, file_server_location,
                                                                     filename))
        sftp.start()
