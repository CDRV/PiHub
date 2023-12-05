##################################################
# PiHub SFTP server uploader
##################################################
# Authors: Simon Brière, Eng. MASc.
#          Mathieu Hamel, Eng. MASc.
##################################################
import logging
import os
import time
import socket
import stat
from os import walk
from os import makedirs

import fabric
from paramiko import BadHostKeyException, AuthenticationException, SSHException, SFTPClient

from libs.hardware.PiHubHardware import PiHubHardware
from libs.utils.Network import Network


class SFTPUploader:

    @staticmethod
    def sftp_send(sftp_config: dict, files_directory_on_server: [str], files_to_transfer: [str],
                  file_transferred_callback: callable = None, check_internet: bool = True) -> bool:
        # Check if Internet connected
        if check_internet:
            PiHubHardware.ensure_internet_is_available()

        # Do the transfer
        logging.info('About to send files to server at ' + sftp_config["hostname"] + ':' + str(sftp_config["port"]))
        file_to_transfer = None
        try:
            with fabric.Connection(host=sftp_config["hostname"], user=sftp_config["username"],
                                   connect_kwargs={'password': sftp_config["password"]},
                                   port=sftp_config["port"], connect_timeout=10) as c:
                c.open()
                client: SFTPClient = c.sftp()
                for file_server_location, file_to_transfer in zip(files_directory_on_server, files_to_transfer):
                    # Create directories on server if needed
                    if not (SFTPUploader.isdir(client, file_server_location)):
                        SFTPUploader.makedirs(client, file_server_location)

                    # Move to directory
                    # client.chdir(file_server_location)
                    file_name = os.path.basename(file_to_transfer)
                    # Query file size from server and compare to local file size
                    local_attr = os.stat(file_to_transfer)
                    local_size = local_attr.st_size
                    remote_file_name = file_server_location + '/' + file_name
                    try:
                        remote_attr = client.lstat(remote_file_name)
                        remote_size = remote_attr.st_size
                        if local_size == remote_size:
                            # Same size on server as local file, skip!
                            logging.info('Skipping ' + file_to_transfer + ': already present on server.')
                            if file_transferred_callback:
                                file_transferred_callback(file_to_transfer)
                            continue
                    except IOError:
                        # File not on server = ok, continue!
                        pass

                    logging.info('Sending ' + file_to_transfer + ' to ' + file_server_location + ' ...')
                    client.put(localpath=file_to_transfer, remotepath=remote_file_name, confirm=True,
                               callback=lambda current, total:
                               SFTPUploader.file_upload_progress(current, total, file_to_transfer,
                                                                 file_transferred_callback))
                    # Update time on server
                    times = (local_attr.st_atime, local_attr.st_mtime)
                    client.utime(remote_file_name, times)

        except (BadHostKeyException, SSHException, AuthenticationException, socket.error, IOError) as exc:
            err_msg = str(exc)
            if hasattr(exc, 'message'):
                err_msg = exc.message + ' ' + err_msg
            if file_to_transfer:
                logging.error('Error occurred transferring ' + str(file_to_transfer) + ': ' + err_msg)
            else:
                logging.error('Error occured while trying to transfer: ' + err_msg)
            return False
        logging.info('Files transfer complete!')
        return True

    @staticmethod
    def sftp_merge_and_send(sftp_config: dict, file_path_on_server: str, file_server_location: str,
                            file_to_transfer: str, temporary_file: str, file_transferred_location: str,
                            file_transferred_callback: callable = None,
                            check_internet: bool = True) -> bool:
        # Check if Internet connected
        if check_internet:
            PiHubHardware.ensure_internet_is_available()

        logging.info('About to get files from server at ' + sftp_config["hostname"] + ':' + str(sftp_config["port"]))
        try:
            with fabric.Connection(host=sftp_config["hostname"], user=sftp_config["username"],
                                   connect_kwargs={'password': sftp_config["password"]},
                                   port=sftp_config["port"], connect_timeout=10) as c:
                c.open()
                client: SFTPClient = c.sftp()
                # Check if the file exist on remote and get it locally
                if not (SFTPUploader.isfile(client, file_path_on_server)):
                    logging.info('No file on server to merge with ' + file_to_transfer)
                else:
                    client.get(file_path_on_server, temporary_file)
                    # Now do the merge in the local file
                    m_point = "/mnt/app"
                    lines = lambda f: [line for line in open(f).read().splitlines()]
                    lines1 = lines(temporary_file)
                    lines2 = lines(file_to_transfer)
                    checks = [line.split(m_point)[-1] for line in lines1]
                    for item in sum([[line for line in lines2 if c in line] for c in checks], []):
                        lines2.remove(item)
                    if os.path.isfile(file_to_transfer):
                        os.remove(file_to_transfer)
                    file_merged = open(file_to_transfer, "a+")
                    for item in lines1 + lines2:
                        file_merged.write(item + "\n")
                    file_merged.close()
                    os.remove(temporary_file)
                    logging.info('Files for ' + file_to_transfer + ' merged')
                # Then send it to ftp
                if not (SFTPUploader.isdir(client, file_server_location)):
                    client.mkdir(file_server_location)

                file_name = os.path.basename(file_to_transfer)
                remote_file_name = file_server_location + '/' + file_name
                local_attr = os.stat(file_to_transfer)
                logging.info('Sending ' + file_to_transfer + ' to ' + file_server_location + ' ...')
                client.put(localpath=file_to_transfer, remotepath=remote_file_name,
                           callback=lambda current, total:
                           SFTPUploader.file_upload_progress(current, total, file_to_transfer,
                                                             file_transferred_callback))
                # Update time on server
                times = (local_attr.st_atime, local_attr.st_mtime)
                client.utime(remote_file_name, times)

                # Move the local file in the transferred directory
                if os.path.isfile(file_transferred_location):
                    os.remove(file_transferred_location)
                os.replace(file_to_transfer, file_transferred_location)

        except (BadHostKeyException, SSHException, AuthenticationException, socket.error, IOError) as exc:
            err_msg = str(exc)
            if hasattr(exc, 'message'):
                err_msg = exc.message + ' ' + err_msg
            if file_to_transfer:
                logging.error('Error occurred transferring ' + str(file_to_transfer) + ': ' + err_msg)
            else:
                logging.error('Error occured while trying to transfer: ' + err_msg)
            return False
        return True

    @staticmethod
    def file_upload_progress(current_bytes: int, total_bytes: int, filename: str = 'Unknown',
                             file_transferred_callback: callable = None):
        pc_transferred = (current_bytes / total_bytes) * 100
        # print(filename + ": " + f'{pc_transferred:.2f}' + "%")
        if pc_transferred >= 100 and file_transferred_callback:
            file_transferred_callback(filename)

    # @staticmethod
    # def sftp_sync(sftp_config: dict, remote_base_path: str, local_base_path: str):
    #     remote_url = sftp_config['username'] + ":" + sftp_config['password'] + '@' + sftp_config["hostname"] + ":" + \
    #                  remote_base_path
    #
    #     cloner = sftpclone.SFTPClone(local_path=local_base_path, remote_url=remote_url, port=sftp_config["port"],
    #                                  delete=False, allow_unknown=True)
    #
    #     cloner.run()
    #     return

    @staticmethod
    def sftp_sync_last(sftp_config: dict, remote_base_path: str, local_base_path: str, check_internet: bool = True):
        folders = [os.path.join(local_base_path + '/local_only/', o)
                   for o in os.listdir(local_base_path + '/local_only/')
                   if os.path.isdir(os.path.join(local_base_path + '/local_only/', o))]
        only_folders = next(walk(local_base_path + '/local_only/'), (None, None, []))[1]
        logging.info('Sensors folder list' + str(only_folders))
        logging.info('Sensors complete folder list' + str(folders))
        # Wait for internet connection
        # PiHubHardware.wait_for_internet_infinite ()
        logging.info("SyncServer: Testing the internet connection...")
        while not (Network.is_internet_connected()):
            logging.info("SyncServer: Connection failed, retry sync in 10min...")
            time.sleep(600)
        logging.info("SyncServer: Pass, syncing files to server...")
        # It is called sync_last but has been modified to sync all files!
        for i in range(0, len(folders)):
            filenames = next(walk(folders[i]), (None, None, []))[2]  # [] if no file
            for j in range(0, len(filenames)):
                file_server_directory = remote_base_path + "/" + only_folders[i]
                filename_2_transfer = folders[i] + "/" + filenames[j]  # all files are synced
                file_server_path = file_server_directory + "/" + filenames[j]
                file_transferred_directory = local_base_path + "/transferred/" + only_folders[i]
                if not os.path.isdir(file_transferred_directory):
                    makedirs(file_transferred_directory)
                file_transferred_location = file_transferred_directory + "/" + filenames[j]
                temp_file = folders[i] + "/tempData.txt"
                SFTPUploader.sftp_merge_and_send(sftp_config, file_path_on_server=file_server_path,
                                                 file_server_location=file_server_directory, temporary_file=temp_file,
                                                 file_transferred_location=file_transferred_location,
                                                 file_to_transfer=filename_2_transfer, check_internet=check_internet)
                logging.info('file at boot ' + str(filename_2_transfer) + ' synced')
            os.rmdir(folders[i])

    @staticmethod
    def makedirs(client: SFTPClient, remotedir: str):
        if SFTPUploader.isdir(client, remotedir):
            pass

        elif SFTPUploader.isfile(client, remotedir):
            raise OSError("a file with the same name as the remotedir, "
                          "'%s', already exists." % remotedir)
        else:
            head, tail = os.path.split(remotedir)
            if head and not SFTPUploader.isdir(client, head):
                SFTPUploader.makedirs(client, head)
            if tail:
                client.mkdir(remotedir)

    @staticmethod
    def isdir(client: SFTPClient, remotepath: str) -> bool:
        try:
            result = stat.S_ISDIR(client.lstat(remotepath).st_mode)
        except IOError:  # no such file
            result = False
        return result

    @staticmethod
    def isfile(client: SFTPClient, remotepath: str) -> bool:
        try:
            result = stat.S_ISREG(client.lstat(remotepath).st_mode)
        except IOError:  # no such file
            result = False
        return result
