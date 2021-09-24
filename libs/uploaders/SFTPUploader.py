##################################################
# PiHub SFTP server uploader
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
import paramiko
import pysftp
import logging
from libs.hardware.PiHubHardware import PiHubHardware


class SFTPUploader:

    @staticmethod
    def sftp_send(sftp_config: dict, file_server_location: str, file_to_transfer: str):
        # Check if Internet connected
        PiHubHardware.ensure_internet_is_available()

        # Do the transfer
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        logging.info('Sending ' + file_to_transfer + ' to server at ' + sftp_config["hostname"] + ':' +
                     str(sftp_config["port"]) + '/' + file_server_location + ' ...')
        try:
            s = pysftp.Connection(host=sftp_config["hostname"], username=sftp_config["username"],
                                  password=sftp_config["password"], port=sftp_config["port"],
                                  cnopts=cnopts)
            if not(s.isdir(file_server_location)):
                s.mkdir(file_server_location)
            with s.cd(file_server_location):
                s.put(file_to_transfer)
            s.close()
            logging.info('File ' + file_to_transfer + ' sent.')
        except (pysftp.exceptions.ConnectionException, pysftp.CredentialException,
                pysftp.AuthenticationException, pysftp.HostKeysException,
                paramiko.SSHException, paramiko.PasswordRequiredException) as exc:
            logging.error('Error occured transferring ' + file_to_transfer + ': ' + str(exc))

