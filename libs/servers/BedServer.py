##################################################
# PiHub main bed communication server
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
from libs.servers.BaseServer import BaseServer

import logging
import socketserver
from os import makedirs
from datetime import datetime


class BedServer(BaseServer, socketserver.StreamRequestHandler):

    server = None

    def __init__(self, server_config: dict):
        super().__init__(server_config=server_config)

    def run(self):
        logging.info('BedServer starting...')
        try:
            self.server = socketserver.ThreadingTCPServer(server_address=(self.hostname, self.port),
                                                          RequestHandlerClass=BedServer)
        except OSError as e:
            logging.critical(e.strerror)
            return
        except OverflowError as e:
            logging.critical(str(e))
            return

        self.server.timeout = 10.0

        logging.info("BedServer started.")
        try:
            self.is_running = True
            self.server.serve_forever()

        finally:
            logging.info("BedServer stopped.")

    def stop(self):
        super().stop()

        if self.server:
            self.server.shutdown()

    def handle(self) -> None:

        # Greet device
        logging.info('Got connection from: ' + self.client_address[0])
        greetings = self.rfile.read(22)
        greetings = greetings.decode('utf-8')
        logging.info('Device identified as: ' + greetings)

        # Establish the correct filename (will be updated each time the sensor is connected
        # Will append the file or create a new one if non-existing
        # filename = Path("/home/pi/Desktop/Data/"+str(datetime.datetime.now().date())+".txt")
        filepath = self.data_path + str(greetings)
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
                d1minidata = self.rfile.read(4)
                if len(d1minidata) == 0:
                    break
                else:
                    x = int.from_bytes(d1minidata,byteorder='little', signed=False)
                    file.write(str(x)+"\t")
            except TimeoutError as e:
                self.rfile.close()
                logging.error("Timeout receiving data.")
                break
        logging.info("Data received! \n")
        file.write("\n")
        file.close()

        # Send file using SFTP
