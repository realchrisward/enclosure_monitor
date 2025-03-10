#

__version__ = "0.1.0"

# %% import libraries
from PySide6.QtCore import QTimer, QFile
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtUiTools import QUiLoader
from datetime import datetime

import glob
import json
import os
import numpy
import re
import socket
import smtplib
import subprocess


# %% define functions
def load_settings(file_path):
	with open(file_path, 'r') as open_file:
		settings = json.load(open_file)
	return settings
	
	
	
def save_settings(settings,file_path):
	with open(file_path,'w') as open_file:
		json.dump(settings,open_file,indent=4)



def send_email(message_dict,settings_dict):
	# %% collect info
	hostname=socket.gethostname()
	hostinfo=socket.gethostbyname_ex(hostname)
	pi_ip=os.popen("hostname -I").read().strip()
	hostinfo[2].append(pi_ip)
	
	smtplib.SMTP_SSL()
	# creates SMTP session
	s = smtplib.SMTP('smtp.gmail.com', 587)
	
	# start TLS for security
	s.starttls()
	
	# Authentication
	s.login(settings_dict['sender_mail'], settings_dict['sender_pass'])
	
	# sending the mail
	for receiver_mail in settings_dict['receiver_mail_list']:
		message = (
			f"From: {settings_dict['sender_mail']}\n"
			+f"To: {receiver_mail}\n"
			+f"Subject: {message_dict['subject']}\n\n"
			+f"{message_dict['body']}\n\n"
			+f"automated message sent from {hostname}\n\n"
			+f"name: {hostinfo[0]}\n"
			+f"aliases: {'|'.join(hostinfo[1])}\n"
			+f"ip: {'|'.join(hostinfo[2])}"
		)
	
		s.sendmail(
			settings_dict['sender_mail'], 
			receiver_mail, 
			message
		)
	
	# terminating the session
	s.quit()	
	
	# print message to terminal - infor for last sender will show
	print(message)



def check_ups(ups_name):
	try:
		result = subprocess.check_output(
			["upsc",ups_name], 
			stderr=subprocess.STDOUT, 
			universal_newlines=True
		)
		status = {}
		for line in result.splitlines():
			if ":" in line:
				key, value = line.split(":",1)
				status[key.strip()] = value.strip()
		return status["ups.status"]
	except subprocess.CalledProcess as e:
		return "NA-process"
	except Exception as e:
		return "NA"
	
	
def read_temp(device_file):
	with open(device_file, 'r') as f:
		lines = f.readlines()
    
	temp_re = re.compile("^.*t=(?P<temperature>.*)$")
	temperature = numpy.nan
	for l in lines:
		if "YES" in l:
			pass
		elif "t=" in l:
			match = temp_re.search(l)
			if match:
				temperature = float(match.group("temperature"))/1000
		else:
			pass
	return temperature


def send_message(settings,text):
	pass


# %% define classes
class MainWindow(QWidget):
	def __init__(self, ui, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		# migrate ui children to parent level of class
		self.ui = ui
		for att, val in ui.__dict__.items():
			setattr(self, att, val)

		self.ui.setWindowTitle("Enclosure Monitor")
		
		# prepare system to communicate with thermometer device
		os.system('modprobe w1-gpio')
		os.system('modprobe w1-therm')
		
		self.base_dir = '/sys/bus/w1/devices/'
		# self.device_folder = glob.glob(self.base_dir + '28*')[0]
		# self.device_file = self.device_folder + '/w1_slave'
		
		self.settings_dict = load_settings('settings.json')
		
		# initialize timers and variables
		self.monitor_timer = QTimer()
		self.monitor_timer.timeout.connect(self.action_monitor)
		
		self.daily_timer = QTimer()
		self.daily_timer.timeout.connect(self.action_daily)
		
		self.startup_timer = QTimer()
		self.startup_timer.timeout.connect(self.action_startup)
		self.startup_timer.setSingleShot(True)
		
		self.monitor_timer_interval = 1000
		self.monitor_timer.start(self.monitor_timer_interval)
		
		self.startup_timer.start(1000*60)
		
		self.daily_timer.start(1000*60*60*24)
				
		
		# self.low_alarm = 4
		# self.high_alarm = 34
		self.temperature = {k: numpy.nan for k in self.settings_dict["device_dict"].keys()}
		self.temperature_history = {k: [numpy.nan] for k in self.settings_dict["device_dict"].keys()}
		
		self.alarm_state = False
		self.alarm_notice_countdown = 0
		# self.alarm_notice_interval_ms = 3*60*60*1000
		
		self.daily_high = {k: 0 for k in self.settings_dict["device_dict"].keys()}
		self.daily_low = {k: 0 for k in self.settings_dict["device_dict"].keys()}
		self.weekly_high = {k: 0 for k in self.settings_dict["device_dict"].keys()}
		self.weekly_low = {k: 0 for k in self.settings_dict["device_dict"].keys()}
		self.daily_avg = {k: 0 for k in self.settings_dict["device_dict"].keys()}
		self.weekly_avg = {k: 0 for k in self.settings_dict["device_dict"].keys()}
		
		self.ups_status = "NA"
		self.ups_status_history = []
		self.startup_sent = False
		# self.daily_sent = False

		self.pushButton_reset_alarm.clicked.connect(self.action_reset_alarm_state)

	def action_monitor(self):
		for k in self.settings_dict["device_dict"].keys():
			self.temperature[k] = read_temp(os.path.join(self.base_dir,self.settings_dict["device_dict"][k],"w1_slave"))
			self.temperature_history[k].append(self.temperature[k])
			if len(self.temperature_history[k]) > 60*60*24*7:
				self.temperature_history[k] = self.temperature_history[-60*60*24*7:]
			#print(self.temperature_history[k])
			self.daily_high[k] = numpy.nanmax(
				self.temperature_history[k][-60*60*24:]
				)
			self.daily_low[k] = numpy.nanmin(self.temperature_history[k][-60*60*24:])
			self.weekly_high[k] = numpy.nanmax(self.temperature_history[k])
			self.weekly_low[k] = numpy.nanmin(self.temperature_history[k])
			self.daily_avg[k] = numpy.nanmean(self.temperature_history[k][-60*60*24:])
			self.weekly_avg[k] = numpy.nanmean(self.temperature_history[k])
			
			self.ups_status = check_ups(self.settings_dict["ups_name"])
			self.ups_status_history.append(self.ups_status)
			if len(self.ups_status_history) > 60:
				self.ups_status_history = self.ups_status_history[-60:]
			
			# print(f"current: {self.temperature:.2F} day_high: {self.daily_high:.2F} day_low: {self.daily_low:.2F} day_avg: {self.daily_avg:.2F}, ups_status: {self.ups_status}")
			if 'OL' not in self.ups_status and 'NA' not in self.ups_status:
				self.alarm_state = True
				if self.alarm_notice_countdown <=0:
					send_email(
						{
							'subject' : 'Power Outage Notice!',
							'body' : f'{datetime.now()}\n\n'
							+'UPS detected power outage\n'
							+f'Current Temperature: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}\n'
							+f'UPS Status: {self.ups_status}\n'
							+f'ALARM STATE: {self.alarm_state}\n'
							+f'Daily AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])} Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])} Daily High {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}\n'
							+f'Weekly AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])} Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])} Weekly High {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}\n'
							+f'ALARM SETPOINTS, Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}, High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}'
						},
						self.settings_dict
					)
					self.alarm_notice_countdown += self.settings_dict["alarm_notice_interval_ms"]
				else:
					self.alarm_notice_countdown -= self.monitor_timer_interval_ms
			
			
			if all(["NA" in i for i in self.ups_status_history]):
				self.alarm_state = True
				if self.alarm_notice_countdown <=0:
					send_email(
						{
							'subject' : 'UPS Status Malfunction!',
							'body' : f'{datetime.now()}\n\n'
							+'UPS Status Malfunction!\n'
							+f'Current Temperature: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}\n'
							+f'UPS Status: {self.ups_status}\n'
							+f'ALARM STATE: {self.alarm_state}\n'
							+f'Daily AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])} Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])} Daily High {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}\n'
							+f'Weekly AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])} Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])} Weekly High {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}\n'
							+f'ALARM SETPOINTS, Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}, High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}'
						},
						self.settings_dict
					)
					self.alarm_notice_countdown += self.settings_dict["alarm_notice_interval_ms"]
				else:
					self.alarm_notice_countdown -= self.monitor_timer_interval_ms
			
			
			
			if self.temperature[k] <= self.settings_dict["low_alarm"][k] or self.temperature[k] >= self.settings_dict["high_alarm"][k]:
				self.alarm_state = True
				if self.alarm_notice_countdown <= 0:
					send_email(
						{
							'subject' : 'Enclosure Temperature Alarm!',
							'body' : f'{datetime.now()}\n\n'
							+'Enclosure Temperature Alarm!\n'
							++f'Current Temperature: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}\n'
							+f'UPS Status: {self.ups_status}\n'
							+f'ALARM STATE: {self.alarm_state}\n'
							+f'Daily AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])} Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])} Daily High {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}\n'
							+f'Weekly AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])} Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])} Weekly High {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}\n'
							+f'ALARM SETPOINTS, Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}, High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}'
						},
						self.settings_dict
					)
					self.alarm_notice_countdown += self.settings_dict["alarm_notice_interval_ms"]
				else:
					self.alarm_notice_countdown -= self.monitor_timer_interval_ms
				print("alarm")
			if self.temperature_history[k][-5:] == [numpy.nan,numpy.nan,numpy.nan,numpy.nan,numpy.nan]:
				self.alarm_state = True
				print("sensor malfunction")
				if self.alarm_notice_countdown <= 0:
					send_email(
						{
							'subject' : 'Sensor Malfunction Notice!',
							'body' : f'{datetime.now()}\n\n'
							+'Sensor Malfunction Notice!\n'
							+f'Current Temperature: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}\n'
							+f'UPS Status: {self.ups_status}\n'
							+f'ALARM STATE: {self.alarm_state}\n'
							+f'Daily AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])} Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])} Daily High {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}\n'
							+f'Weekly AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])} Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])} Weekly High {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}\n'
							+f'ALARM SETPOINTS, Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}, High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}'
						},
						self.settings_dict
					)
					self.alarm_notice_countdown += self.settings_dict["alarm_notice_interval_ms"]
				else:
					self.alarm_notice_countdown -= self.monitor_timer_interval_ms
				print("error")
					
		self.label_cur_temp.setText(f'Current Temp: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}')
		self.label_daily_avg.setText(f'Daily Avg: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])}')
		self.label_daily_low.setText(f'Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])}')
		self.label_daily_high.setText(f'Daily High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}')
		self.label_weekly_avg.setText(f'Weekly Avg: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])}')
		self.label_weekly_low.setText(f'Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])}')
		self.label_weekly_high.setText(f'Weekly High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}')
		self.label_cur_ups.setText(f'UPS Status: {self.ups_status}')
		self.label_alarm_status.setText(f'Alarm Status: {self.alarm_state}')
		self.label_high_alarm_set.setText(f'High Alarm SetPoint: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}')
		self.label_low_alarm_set.setText(f'Low Alarm SetPoint: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}')
		self.label_datetime.setText(f'Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
			
	

	def action_daily(self):
		send_email(
			{
				'subject' : 'daily status update from enclosure monitor',
				'body' : f'{datetime.now()}\n\n'
				+'daily status update from enclosure monitor\n'
				+f'Current Temperature: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}\n'
				+f'UPS Status: {self.ups_status}\n'
				+f'ALARM STATE: {self.alarm_state}\n'
				+f'Daily AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])} Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])} Daily High {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}\n'
				+f'Weekly AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])} Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])} Weekly High {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}\n'
				+f'ALARM SETPOINTS, Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}, High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}'
			},
			self.settings_dict
			)

	def action_startup(self):
		if not self.startup_sent:
			send_email(
				{
					'subject' : 'startup notification from enclosure monitor',
					'body' : f'{datetime.now()}\n\n'
					+'startup notification from enclosure monitor\n'
					+f'Current Temperature: {("|").join([f"{key}:{val:.2F} C" for key,val in self.temperature.items()])}\n'
					+f'UPS Status: {self.ups_status}\n'
					+f'ALARM STATE: {self.alarm_state}\n'
					+f'Daily AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_avg.items()])} Daily Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_low.items()])} Daily High {("|").join([f"{key}:{val:.2F} C" for key,val in self.daily_high.items()])}\n'
					+f'Weekly AVG {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_avg.items()])} Weekly Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_low.items()])} Weekly High {("|").join([f"{key}:{val:.2F} C" for key,val in self.weekly_high.items()])}\n'
					+f'ALARM SETPOINTS, Low: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["low_alarm"].items()])}, High: {("|").join([f"{key}:{val:.2F} C" for key,val in self.settings_dict["high_alarm"].items()])}'
				},
				self.settings_dict
			)

			self.startup_sent = True
			
	def action_reset_alarm_state(self):
		self.alarm_state = False
	
	
def main():
	
	#args = []
	#args.append("--platform")
	#args.append("offscreen")
	
	print("starting")
	loader = QUiLoader()
	
	app = QApplication()
	
	ui_file = QFile(os.path.join(os.path.dirname(__file__),"enclosure_monitor.ui"))
	
	ui = loader.load(ui_file)
	
	window = MainWindow(ui)
	
	window.version_info = {
		"main":__version__
	}
	
	window.ui.show()
	
	app.exec()

	
if __name__ == "__main__":
	main()
