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

from sftpclone import sftpclone


class SFTPUploader:

    @staticmethod
    def sftp_send(sftp_config: dict, files_path_on_server: [str], files_to_transfer: [str]) -> bool:
        # Check if Internet connected
        PiHubHardware.ensure_internet_is_available()

        # Do the transfer
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        logging.info('About to send files to server at ' + sftp_config["hostname"] + ':' + str(sftp_config["port"]))
        try:
            with pysftp.Connection(host=sftp_config["hostname"], username=sftp_config["username"],
                                   password=sftp_config["password"], port=sftp_config["port"],
                                   cnopts=cnopts) as s:
                for file_server_location, file_to_transfer in zip(files_path_on_server, files_to_transfer):
                    if not(s.isdir(file_server_location)):
                        s.mkdir(file_server_location)
                    with s.cd(file_server_location):
                        s.put(localpath=file_to_transfer, preserve_mtime=True)
                        logging.info('Sending ' + file_to_transfer + ' to ' + file_server_location + ' ...')
                # s.close()
            # logging.info('File ' + file_to_transfer + ' sent.')
        except (pysftp.exceptions.ConnectionException, pysftp.CredentialException,
                pysftp.AuthenticationException, pysftp.HostKeysException,
                paramiko.SSHException, paramiko.PasswordRequiredException) as exc:
            logging.error('Error occured transferring ' + file_to_transfer + ': ' + str(exc))
            return False

        logging.info('Files transfer complete!')
        return True

    @staticmethod
    def sftp_sync(sftp_config: dict, remote_base_path: str, local_base_path: str):
        remote_url = sftp_config['username'] + ":" + sftp_config['password'] + '@' + sftp_config["hostname"] + ":" + \
                     remote_base_path

        cloner = sftpclone.SFTPClone(local_path=local_base_path, remote_url=remote_url, port=sftp_config["port"],
                                     delete=False, allow_unknown=True)

        cloner.run()

