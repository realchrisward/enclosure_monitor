# enclosure_monitor
instruction guide, parts list, and code for monitoring environmental enclosures

# setup raspberry pi
1. download and install uv `curl -LsSf https://astral.sh/uv/install.sh | sh`
1. reboot the pi `sudo reboot`
1. clone repository (recommended location is in "git" subfolder of home directory) <br/>`git clone https://github.com/realchrisward/enclosure_monitor.git`
1. enter the repository directory `cd enclosure_monitor`
1. create venv (python 3.12) `uv venv --python 3.12`
1. open /boot/config.txt to edit `sudo nano /boot/config.txt`
1. at end of file add entry to enable 1-wire com `dtoverlay=w1-gpio`
1. reboot the pi `sudo reboot`

# test the connection with the temperature probe

# notes
sources used to help create this guide
* https://alonsostepanova.wordpress.ncsu.edu/raspberry-pi-freezer-alarm-wifi/
