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
1. add dependencies for NUT communication with UPS `sudo apt install nut`
1. edit ups and nut config <br/>
`sudo nano /etc/nut/ups.config` <br/><br/>
`[UPS_TMS]` <br/>
`driver = usbhid-ups` <br/>
`desc = "ups for temperature monitoring system"` <br/>
`port = auto` <br/>
`vendorid = 0764` <br/>
`productid = 0501` <br/>
<br/><br/><br/>
`sudo nano /etc/not/nut.config`<br/><br/>
`MODE=netserver`<br/>
1. update settings.json.template, rename to settings.json. (update the ups name [name used for ups.config], the temperature probe device addresses [list of devices are directories at /sys/bus/w1/devices/], email info for email notification sending, and email info for contacts for daily and alarm notices.


# test the connection with the temperature probe
1. go to the directory holding probe one wire comm records `cd /sys/bus/w1/devices/` and enter the folder for the probe (connecting one at a time can help identify which probe has which address)
2. read the w1_slave file to confirm that the probe is getting reading `cat w1_slave`
3. the second line should look like this: `78 01 55 05 7f a5 a5 66 ed t=23500` the numper after t= is the temperature in C (times 1000)

# notes
* to enable automated running at boot time, you can call a shell script to launch the enclosure monitor with from a .desktop file in the "/etc/xdg/autostart" directory (an example desktop file is in the repository)
* inspiration to create this project from https://alonsostepanova.wordpress.ncsu.edu/raspberry-pi-freezer-alarm-wifi/
