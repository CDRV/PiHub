##################################################
# PiHub SFTP server uploader
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
import paramiko
import pysftp
import logging
import os
from os import walk
from libs.hardware.PiHubHardware import PiHubHardware

from sftpclone import sftpclone


class SFTPUploader:

    @staticmethod
    def sftp_send(sftp_config: dict, files_directory_on_server: [str], files_to_transfer: [str],
                  file_transferred_callback: callable = None, check_internet: bool = True) -> bool:
        # Check if Internet connected
        if check_internet:
            PiHubHardware.ensure_internet_is_available()

        # Do the transfer
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        logging.info('About to send files to server at ' + sftp_config["hostname"] + ':' + str(sftp_config["port"]))
        try:
            with pysftp.Connection(host=sftp_config["hostname"], username=sftp_config["username"],
                                   password=sftp_config["password"], port=sftp_config["port"],
                                   cnopts=cnopts) as s:
                for file_server_location, file_to_transfer in zip(files_directory_on_server, files_to_transfer):
                    if not (s.isdir(file_server_location)):
                        s.mkdir(file_server_location)
                    with s.cd(file_server_location):
                        s.put(localpath=file_to_transfer, preserve_mtime=True,
                              callback=lambda current, total:
                              SFTPUploader.file_upload_progress(current, total, file_to_transfer,
                                                                file_transferred_callback))
                        logging.info('Sending ' + file_to_transfer + ' to ' + file_server_location + ' ...')
                # s.close()
            # logging.info('File ' + file_to_transfer + ' sent.')
        except (pysftp.exceptions.ConnectionException, pysftp.CredentialException,
                pysftp.AuthenticationException, pysftp.HostKeysException,
                paramiko.SSHException, paramiko.PasswordRequiredException) as exc:
            logging.error('Error occurred transferring ' + file_to_transfer + ': ' + str(exc))
            return False

        logging.info('Files transfer complete!')
        return True

    @staticmethod
    def sftp_merge(sftp_config: dict, file_path_on_server: str, file_to_transfer: str, temporary_file: str,
                   file_transferred_callback: callable = None, check_internet: bool = True) -> bool:
        # Check if Internet connected
        if check_internet:
            PiHubHardware.ensure_internet_is_available()

        # Check if the file exist on remote and get it locally
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        logging.info('About to get file from server at ' + sftp_config["hostname"] + ':' + str(sftp_config["port"]))
        try:
            with pysftp.Connection(host=sftp_config["hostname"], username=sftp_config["username"],
                                   password=sftp_config["password"], port=sftp_config["port"],
                                   cnopts=cnopts) as s:
                if not (s.isfile(file_path_on_server)):
                    logging.info('No file on server to merge with ' + file_to_transfer)
                    return True
                s.get(file_path_on_server, temporary_file)
        except (pysftp.exceptions.ConnectionException, pysftp.CredentialException,
                pysftp.AuthenticationException, pysftp.HostKeysException,
                paramiko.SSHException, paramiko.PasswordRequiredException) as exc:
            logging.error('Error occurred transferring ' + file_path_on_server + ': ' + str(exc))
            return False

        # Now do the merge in the local file
        m_point = "/mnt/app"
        lines = lambda f: [l for l in open(f).read().splitlines()]
        lines1 = lines(temporary_file)
        lines2 = lines(file_to_transfer)
        checks = [l.split(m_point)[-1] for l in lines1]
        for item in sum([[l for l in lines2 if c in l] for c in checks], []):
            lines2.remove(item)
        if os.path.isfile(file_to_transfer):
            os.remove(file_to_transfer)
        file_merged = open(file_to_transfer, "a+")
        for item in lines1 + lines2:
            file_merged.write(item + "\n")
        file_merged.close()
        os.remove(temporary_file)
        logging.info('Files for ' + file_to_transfer + ' merged')
        return True

    @staticmethod
    def file_upload_progress(current_bytes: int, total_bytes: int, filename: str = 'Unknown',
                             file_transferred_callback: callable = None):
        pc_transferred = (current_bytes / total_bytes) * 100
        # print(filename + ": " + f'{pc_transferred:.2f}' + "%")
        if pc_transferred >= 100 and file_transferred_callback:
            file_transferred_callback(filename)

    @staticmethod
    def sftp_sync(sftp_config: dict, remote_base_path: str, local_base_path: str):
        remote_url = sftp_config['username'] + ":" + sftp_config['password'] + '@' + sftp_config["hostname"] + ":" + \
                     remote_base_path

        cloner = sftpclone.SFTPClone(local_path=local_base_path, remote_url=remote_url, port=sftp_config["port"],
                                     delete=False, allow_unknown=True)

        cloner.run()

    @staticmethod
    def sftp_sync_last(sftp_config: dict, remote_base_path: str, local_base_path: str):
        folders = [os.path.join(local_base_path, o) for o in os.listdir(local_base_path)
                   if os.path.isdir(os.path.join(local_base_path, o))]
        only_folders = next(walk(local_base_path), (None, None, []))[1]
        logging.info('Sensors folder list' + str(only_folders))

        for i in range(0, len(folders)):
            filenames = next(walk(folders[i]), (None, None, []))[2]  # [] if no file
            file_server_directory = remote_base_path + "/" + only_folders[i]
            filename_2_transfer = folders[i] + "/" + filenames[0]  # Only the last file in directory is 0 (change to
            # something more robust)
            file_server_path = file_server_directory + "/" + filenames[0]
            temp_file = folders[i] + "/tempData.txt"
            SFTPUploader.sftp_merge(sftp_config, file_path_on_server=file_server_path,
                                    temporary_file=temp_file, file_to_transfer=filename_2_transfer)
            SFTPUploader.sftp_send(sftp_config, files_directory_on_server=[file_server_directory],
                                   files_to_transfer=[filename_2_transfer])
            logging.info('file at boot' + str(filename_2_transfer) + ' synced')
