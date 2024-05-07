from libs.servers.BaseServer import BaseServer
from http.server import ThreadingHTTPServer

import logging
import os


class WatchServerBase(BaseServer):
    server: ThreadingHTTPServer | None = None
    _request_handler = None
    processed_files = []
    _connected_devices = []

    def __init__(self, server_config: dict, request_handler):
        super().__init__(server_config=server_config)
        self.server_base_folder = server_config['server_base_folder']
        self.send_logs_only = server_config['send_logs_only']
        self.minimal_dataset_duration = server_config['minimal_dataset_duration']

        self._request_handler = request_handler
        self._request_handler.base_server = self

    def run(self):
        logging.info(self.__class__.__name__ + ' starting...')
        self.server = ThreadingHTTPServer((self.hostname, self.port), self._request_handler)
        self.server.timeout = 5  # 5 seconds timeout should be ok since we are usually on local network
        self.is_running = True
        logging.info(self.__class__.__name__ + ' started on port ' + str(self.port))

        # Thread will wait here
        self.server.serve_forever()
        self.server.server_close()
        logging.info(self.__class__.__name__ + ' stopped.')

    def stop(self):
        super().stop()

        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def new_file_received(self, device_name: str, filename: str):
        logging.debug(self.__class__.__name__ + ' - unhandled new file received')

    def device_disconnected(self, device_name: str):
        # logging.debug(self.__class__.__name__ + ' - unhandled device disconnected')
        if device_name in self._connected_devices:
            self._connected_devices.remove(device_name)

    def device_connected(self, device_name: str):
        if device_name not in self._connected_devices:
            self._connected_devices.append(device_name)

    @staticmethod
    def move_files(source_files, target_folder):
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

    @staticmethod
    def move_folder(source_folder, target_folder):
        import shutil
        try:
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)
            shutil.move(source_folder, target_folder)
        except shutil.Error as exc:
            error = exc.strerror
            if not error:
                error = 'Unknown error'
            logging.critical('Error moving ' + source_folder + ' to ' + target_folder + ': ' + error)

    def file_was_processed(self, full_filepath: str):
        # Mark file as processed - will be moved later on to prevent conflicts
        self.processed_files.append(full_filepath)

    def move_processed_files(self):
        self.move_files(self.processed_files, 'Processed')
        self.processed_files.clear()

    @staticmethod
    def remove_empty_folders(path_abs):
        walk = list(os.walk(path_abs))
        for path, _, _ in walk[::-1]:
            if len(os.listdir(path)) == 0:
                os.rmdir(path.replace("/", os.sep))
