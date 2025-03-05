#

__version__ = "0.1.0"

# %% import libraries
from PySide6.QtCore import QTimer, QFile
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtUiTools import QUiLoader
import os
import glob
import re



# %% define functions
def read_temp(device_file):
	with open(device_file, 'r') as f:
		lines = f.readlines()
    
	temp_re = re.compile("^.*t=(?P<temperature>.*)$")
	temperature = "NA"
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
		self.device_folder = glob.glob(self.base_dir + '28*')[0]
		self.device_file = self.device_folder + '/w1_slave'
		
		# initialize timers and variables
		self.monitor_timer = QTimer()
		self.monitor_timer.timeout.connect(self.action_monitor)
		self.daily_timer = QTimer()
		self.daily_timer.timeout.connect(self.action_daily)
		self.monitor_timer_interval = 1000
		self.monitor_timer.start(self.monitor_timer_interval)
		self.daily_timer.start(1000*60*60*24)
		self.low_alarm = 4
		self.high_alarm = 34
		self.temperature = "NA"
		self.temperature_history = []
		self.alarm_state = False
		self.alarm_notice_countdown = 0
		self.alarm_notice_interval_ms = 3*60*60*1000
		
		self.daily_high = 0
		self.daily_low = 0
		self.weekly_high = 0
		self.weekly_low = 0
		self.daily_avg = 0
		self.weekly_avg = 0


	def action_monitor(self):
		self.temperature = read_temp(self.device_file)
		self.temperature_history.append(self.temperature)
		if len(self.temperature_history) > 60*60*24*7:
			self.temperature_history = self.temperature_history[-60*60*24*7:]
		self.daily_high = max(self.temperature_history[-60*60*24:])
		self.daily_low = min(self.temperature_history[-60*60*24:])
		self.weekly_high = max(self.temperature_history)
		self.weekly_low = min(self.temperature_history)
		self.daily_avg = sum(self.temperature_history[-60*60*24:])/len(self.temperature_history[-60*60*24:])
		self.weekly_avg = sum(self.temperature_history)/len(self.temperature_history)
		
		print(f"current: {self.temperature:.2F} day_high: {self.daily_high:.2F} day_low: {self.daily_low:.2F} day_avg: {self.daily_avg:.2F}")
		
		if self.temperature <= self.low_alarm or self.temperature >= self.high_alarm:
			self.alarm_state = True
			if self.alarm_notice_countdown <= 0:
				send_message('x','y')
				self.alarm_notice_countdown += self.alarm_notice_interval_ms
			else:
				self.alarm_notice_countdown -= self.monitor_timer_interval
			print("alarm")
		if self.temperature_history[-5:] == ["NA","NA","NA","NA","NA"]:
			print("sensor malfunction")
			if self.alarm_notice_countdown <= 0:
				send_message('x','y')
				self.alarm_notice_countdown += self.alarm_notice_interval_ms
			else:
				self.alarm_notice_countdown -= self.monitor_timer_interval
			print("error")
		

		
	def action_daily(self):
		pass

	
	
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
