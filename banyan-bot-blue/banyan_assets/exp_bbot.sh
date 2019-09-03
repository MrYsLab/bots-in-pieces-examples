#!/bin/bash
backplane &
sleep 3
sudo python3 /home/pi/exp_pro_gateway.py &
sleep 5
sudo python3 /home/pi/robot_control.py &
sleep 2
sudo python3 /home/pi/bluetooth_gateway.py &
sleep 4



