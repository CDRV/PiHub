#!/bin/sh
clear

#sudo raspi-config # for Serial options

sudo qmicli -d /dev/cdc-wdm0 --dms-set-operating-mode='online'


#FOR TESTS
#sudo qmicli -d /dev/cdc-wdm0 --dms-get-operating-mode
#sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength
#sudo qmicli -d /dev/cdc-wdm0 --nas-get-home-network

sudo ip link set wwan0 down
echo 'Y' | sudo tee /sys/class/net/wwan0/qmi/raw_ip
sudo ip link set wwan0 up
sudo qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='sp.telus.com',username='pi',password=' ',ip-type=4" --client-no-release-cid

sudo udhcpc -i wwan0
ip a s wwan0
sudo ifmetric wwan0 300