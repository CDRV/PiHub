import os
from os import walk
import pysftp
from pathlib import Path

#FTP Function
def ftpGo(fileSvrLoc, file2Transfert):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None  
    with pysftp.Connection(host='telesante.cdrv.ca',username='test',password='Test1234!',port=40091,cnopts=cnopts) as s:      
        if not(s.isdir(fileSvrLoc)):
            s.mkdir(fileSvrLoc)
        with s.cd(fileSvrLoc):
            s.put(file2Transfert)
        
#List all lasts files and transfer it
d = '/home/pi/Desktop/Data'
folders = [os.path.join(d, o) for o in os.listdir(d) 
                    if os.path.isdir(os.path.join(d,o))]
onlyFolders = next(walk(d), (None, None, []))[1]
print(onlyFolders)

for i in range(0, len(folders)):
    filenames = next(walk(folders[i]), (None, None, []))[2]  # [] if no file
    fileServerLocation = "/CdrvBed01/" + onlyFolders[i]
    filename2Transfert = folders[i] + '/' + filenames[0]
    print(fileServerLocation)
    print(filename2Transfert)
    ftpGo(fileServerLocation, filename2Transfert)
    