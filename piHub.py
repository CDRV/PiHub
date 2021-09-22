# Mathieu Hamel, Eng. MSc
# Modif AG add restart 4G connection + FTP transfert at each update
# CSSS-IUGS, Research Center on Aging
# Description: Server script installed on Raspberry PI3 with SIM7600 LTE Modem.
#              The script listens for a connection with a Bed sensor (ESP8266 D1 Mini IoT boards)
#              and will receive 60 samples logged into RAM (i.e: ESP8266 will record 1 sample per minutes
#              and thus, will send 1 hour worth of data using a TCP socket.
#              This data is recorded in a file named by date (1 file per day)
#              Another script will be call using a Cron JOB and will send these files to the server

import socket
import sys
import datetime
import os
from pathlib import Path
import pysftp
import time
import urllib.request

# IP of the server and port to use (Bed sensors will connect to this
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = '192.168.4.1'
port = 3000
sock.bind((host,port))

#Create a function to check the internet connexion
def connect(host='http://google.com'):
    try:
        urllib.request.urlopen(host) #Python 3.x
        return True
    except:
        return False
#Create a function for the FTP transfert    
def ftpGo(fileSvrLoc, file2Transfert):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None  
    with pysftp.Connection(host='telesante.cdrv.ca',username='test',password='Test1234!',port=40091,cnopts=cnopts) as s:      
        if not(s.isdir(fileSvrLoc)):
            s.mkdir(fileSvrLoc)
        with s.cd(fileSvrLoc):
            s.put(file2Transfert)

# Main loop
sock.listen(1)
while(1):
    conn, addr = sock.accept()
    conn.settimeout(10.0)
    
    # Will print in console the greetings from the sensor..
    print('Got connection from: ',addr)
    greetings = conn.recv(22)
    greetings = greetings.decode('utf-8')
    print(greetings)
    
    # Establish the correct filename (will be updated each time the sensor is connected
    # Will append the file or create a new one if non-existing
    # filename = Path("/home/pi/Desktop/Data/"+str(datetime.datetime.now().date())+".txt")
    isDir = os.path.isdir(Path("/home/pi/Desktop/Data/"+str(greetings)))
    if isDir == 0:
        os.mkdir(Path("/home/pi/Desktop/Data/"+str(greetings)))
    filename = Path("/home/pi/Desktop/Data/"+str(greetings)+"/"+str(datetime.datetime.now().date())+".txt")
    file = open(filename,'a')
    file.write(str(datetime.datetime.now()) + "\t")
    
    # Loop to transfer data (4 bytes at a time - UINT32 are read from RAM and transmitted by ESP
    while(sock.connect):
        try:
            D1miniData = conn.recv(4)        
            if len(D1miniData) == 0:
                break
            else:
                Data = bytearray(D1miniData)
                x = int.from_bytes(D1miniData,byteorder='little',signed=False)
                file.write(str(x)+"\t")
        except socket.timeout as e:
            conn.settimeout(1.0)
            while(1):
                try:
                    scrap = conn.recv(1)
                except socket.timeout as e:
                    break
            print("timout receiving Data")
            break
    print("Data received! \n")
    file.write("\n")
    file.close()
    #sock.close
    
    #reseting the wireless 4G connexion to make sure its active
#     cmd1 = 'sudo ifconfig wwan0 down'
#     os.system(cmd1)
#     time.sleep(1)
#     cmd2 = 'sudo ifconfig wwan0 up'
#     os.system(cmd2)
#     time.sleep(1)
#    cmd3 = 'sh /home/pi/Desktop/Startup/atstart.sh'
#    os.system(cmd3)
#    time.sleep(5)

    #Save the right path for the file to transfert
    fileServerLocation = "/CdrvBed01/" + str(greetings)
    filename2Transfert = "/home/pi/Desktop/Data/"+str(greetings)+"/"+str(datetime.datetime.now().date())+".txt"
   
    #If the connection is Up, do the FTP transfert else try a second time
    if connect():
        ftpGo(fileServerLocation, filename2Transfert)
    else :
      #Try reseting the wireless 4G connexion to make sure its active with more time
        #cmd1 = 'sudo ifconfig wwan0 down'
        #os.system(cmd1)
        #time.sleep(1)
        #cmd2 = 'sudo ifconfig wwan0 up'
        #os.system(cmd2)
        #time.sleep(1)
        cmd3 = 'sh /home/pi/Desktop/Startup/atstart.sh'
        os.system(cmd3)
        time.sleep(5)
        if connect(): #And try a second time or else reboot the Pi
            ftpGo(fileServerLocation, filename2Transfert)
        else :
            cmdReboot = 'sudo reboot'
            os.system(cmdReboot)
