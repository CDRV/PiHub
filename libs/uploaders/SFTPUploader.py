##################################################
# PiHub SFTP server uploader
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
import pysftp

from libs.uploaders.BaseUploader import BaseUploader


class SFTPUploader(BaseUploader):

    def __init__(self, sftp_config: dict):
        super().__init__(sftp_config)
        self.username = sftp_config["username"]
        self.password = sftp_config["password"]

    def sftp_send(self, file_server_location: str, file_to_transfer: str):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(host=self.hostname, username=self.username, password=self.password, port=self.port,
                               cnopts=cnopts) as s:
            if not(s.isdir(file_server_location)):
                s.mkdir(file_server_location)
            with s.cd(file_server_location):
                s.put(file_to_transfer)
