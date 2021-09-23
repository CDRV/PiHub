##################################################
# PiHub base server uploader
##################################################
# Authors: Simon Brière, Eng. MASc.
##################################################


class BaseUploader:

    def __init__(self, uploader_config):
        self.hostname = uploader_config["hostname"]
        self.port = uploader_config["port"]
