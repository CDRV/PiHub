# PiHub
Multi-network (cellular, wi-fi &amp; ethernet) sensor and data hub with local repository and remote transfer on SFTP / opentera server

## Description
This project was designed to run on a Raspberry Pi board with a cellular hat (Waveshare SIM7600CE 4G HAT - https://www.waveshare.com/product/raspberry-pi/hats/iot/sim7600ce-4g-hat.htm).

Main features of the project includes:
  * Local Wi-Fi hub on which devices can connect and provides direct internet access
    * Over cellular network
    * Over connected ethernet cable
  * Data transfer hub:
    * Locally connected devices can transfer data on the hub
    * The hub keeps a local backup of the data and can then optionnaly transfer the data to:
      * An SFTP server
      * OpenTera (https://github.com/introlab/opentera) server

## Requirements
* Miniconda 

### Miniconda installation

1. Open a terminal
2. `wget http://repo.continuum.io/miniconda/Miniconda3-py39_4.9.2-Linux-aarch64.sh -O ~/miniconda3/miniconda.sh`
3. `conda init bash`
4. Close the terminal and start it again (or reload bash)

## Pi setup

### Installation
  1. Clone the repository directly into `/home/pi/Desktop` folder (a PiHub folder will be created - you can also choose any other place you want): 
     `git clone https://github.com/CDRV/PiHub.git`
  2. Create Python virtual environment:
     1. `cd /home/pi/Desktop/PiHub`
     2. `chmod +x create_conda_venv.sh`
     3. `./create_conda_venv.sh`
     4. Make a copy of the default config file `cp /home/pi/Desktop/PiHub/config/PiHub_Defaults.json /home/pi/Desktop/PiHub/config/PiHub.json` 
     5. Edit the config file `/home/pi/Desktop/PiHub/config/PiHub.json` with the appropriate values
     6. Setup the cron tasks using `sudo crontab -e` and the crontab job listed in the `/home/pi/Desktop/PiHub/setup/crontab.txt` file
     7. Setup and enable the main pihub service using<br>
        `sudo cp /home/pi/Desktop/PiHub/setup/pihub.service /etc/systemd/system/pihub.service`<br>
        `sudo systemctl enable pihub.service`
        `sudo systemctl start pihub.service`
     
### OpenTera configuration
Edit the `PiHub.json` configuration file:
* `WatchServer` 
  * `"transfer_type": "opentera"`
* `OpenTera`
  * `"device_register_key": "(insert key)"` -> Device register key can be obtained by logging in on the target server and going in the "About" screen. Only super admins can see that key.
  * `"default_session_type_id": (id)` -> Session type ID to use to create session.

### Service usage
To check if the service is running: `systemctl status pihub.service`
To query service output (log): `journalctl -u pihub.service`

## Local development environment setup
If not developping directly on a Raspberry Pi, a virtual Python environment (venv) is suggested. 

1. Install Python (see requirement version above)
2. Create a virtual environment:
   1. Install and setup miniconda for your OS 
   2. Open a command line interface
   3. Go to the PiHub folder
   4. Create the virtual environment: `create_conda_venv`

