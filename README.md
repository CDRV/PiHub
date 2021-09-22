# PiHub
Multi-network (cellular, wi-fi &amp; ethernet) sensor and data hub with local repository and remote transfer on SFTP / opentera server

## Description
This project was designed to run on a Raspberry Pi board with a cellular hat (Waveshare SIM7600CE 4G HAT - https://www.waveshare.com/product/raspberry-pi/hats/iot/sim7600ce-4g-hat.htm).

Main features of the project includes:
  * Local wifi hub on which devices can connect and provides direct internet access
    * Over cellular network
    * Over connected ethernet cable
  * Data transfer hub:
    * Locally connected devices can transfer data on the hub
    * The hub keeps a local backup of the data and can then optionnaly transfer the data to:
      * An SFTP server
      * OpenTera (https://github.com/introlab/opentera) server

## Requirements
Python 3.8

## Pi setup
  1. Pull the repository directly into `/home/pi/Desktop` folder (a PiHub folder will be created)
  2. Edit the config file `/home/pi/Desktop/PiHub/config/PiHub.json`
  3. Setup the cron tasks using `sudo crontab -e` and the crontab job listed in the `/home/pi/Desktop/PiHub/setup/crontab.txt` file
  4. Setup and enable the main pihub service using<br>
     `sudo cp /home/pi/Desktop/PiHub/setup/pihub.service /etc/systemd/system/pihub.service`<br>
     `sudo systemctl enable pihub.service`
     
### Service usage
To check if the service is running: `systemctl status pihub.service`
To query service output (log): `journalctl -u pihub.service`

## Local development environment setup
If not developping directly on a Raspberry Pi, a virtual Python environment (venv) is suggested. 

1. Install Python (see requirement version above)
2. Create a virtual environment:
  1. Open a command line interface
  2. Go to the PiHub folder
  3. Create the virtual environment: `python -m venv venv`
  4. Enable the virtual environment: <br>
     On Mac/Linux: `source venv/bin/activate`<br>
     On Windows: `venv\Scripts\activate.bat`
  5. Install requirements: `pip install -r requirements.txt`

