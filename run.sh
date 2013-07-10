export QUICK2WIRE_API_HOME=/home/pi/nrf/quick2wire-python-api-master
export PYTHONPATH=$PYTHONPAT:$QUICK2WIRE_API_HOME
sudo gpio-admin unexport 8 
sudo gpio-admin unexport 25
#python3 nRF24L01p.py
python3 message_proxy.py

