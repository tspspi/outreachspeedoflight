from time import sleep
import time
from math import exp

import socket
import math
import json
import os
from pathlib import Path
import queue

import numpy as np

import random

import logging
import datetime

class MSO5000Oscilloscope_Simulation:
	def __init__(self, filename=None, logger = None):
		self._filename = filename
		self._logger = logger

	def setChannelEnable(self, channel, enabled):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Channel {channel} set to {enabled}")
		return

	def setTriggerSweep_Single(self):
		if self._logger is not None:
			self._logger.debug("[OSCISIM] Setting trigger mode to single")
	def setTriggerSweep_Auto(self):
		if self._logger is not None:
			self._logger.debug("[OSCISIM] Setting trigger mode to auto")
	def setTriggerSweep_Normal(self):
		if self._logger is not None:
			self._logger.debug("[OSCISIM] Setting trigger mode to normal")

	def setWaveformMode_Normal(self):
		if self._logger is not None:
			self._logger.debug("[OSCISIM] Setting waveform mode to normal")
	def setWaveformMode_Raw(self):
		if self._logger is not None:
			self._logger.debug("[OSCISIM] Setting waveform mode to raw")
	def setWaveformFormat_ASCII(self):
		if self._logger is not None:
			self._logger.debug("[OSCISIM] Setting waveform mode to ASCII")

	def waitTriggerDone(self):
		while not self.isTriggerDone():
			pass

	def isTriggerDone(self):
		delay = random.uniform(0.2, 0.9)
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Sleeping {delay} s")
		sleep(delay)
		return random.choice([True, False])

	def setTriggerSource(self, channel):
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel for trigger source has to be in range 1 - 4")
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting trigger source to channel {channel}")
	def setTriggerLevel(self, level):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting trigger level to {level}")

	def setTimebasePerDivision(self, secondsPerDivision):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting to {secondsPerDivision} s/div")
	def setTimebaseModeMain(self):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting timebase mode to main")

	def run(self):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Run mode")
	def stop(self):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Stop mode")

	def setChannelOffset(self, channel, offset):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting channel offset for channel {channel} to {offset}")
	def setChannelScale(self, channel, perdivision):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting channel scale for channel {channel} to {perdivision}")

	def setCounterEnabled(self, enable):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting counter status to {enable}")
	def setCounterChannel(self, channel):
		channel = int(channel)
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel has to be in range 1 - 4")
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting counter channel source to {channel}")
	def setCounterMode(self, mode):
		if mode == "f":
			mode = "frequency"
		elif mode == "t":
			mode = "period"
		else:
			raise ValueError("Mode has to be (f)requency or (t)ime")
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Setting counter mode {mode}")
	def queryCounter(self):
		if self._logger is not None:
			self._logger.debug(f"[OSCISIM] Queried random counter data")
		return random.uniform(60,100)


	def queryData(self, channel):
		if isinstance(channel, list) or isinstance(channel, tuple):
			res = {
				'payload' : 'data'
			}
			for chan in channel:
				res[chan] = self.queryData(chan)
			return res

		if (channel < 1) or (channel > 4):
			raise ValueError("Invalid channel number (1-4 valid)")

		# ToDo: Implement querying data form our file. Currently we fill with random stuff ...
		data = np.random.uniform(low=0.0, high=1.0, size=(1024,))

		dt = 0
		if channel == 2:
			dt = 0.5 + random.uniform(0,2)
			sampledt = dt / (12 / 1024)
			self._logger.debug(f"[OSCISIM] Simulated delay is {sampledt}")

		# Trace logistic function
		for i, arg in enumerate(np.linspace(-6, 6, 1024)):
			v = 10 / (1 + exp(-(arg - dt)))
			data[i] = data[i] + v

		return data


class MSO5000Oscilloscope:
	def __init__(self,ipaddr="10.0.0.196",port=5555):
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.connect((ipaddr, port))

		print(self.scpiCommand("*IDN?"))

		# Enable channels 1 and 2
		self.setChannelEnable(1, True)
		self.setChannelEnable(2, True)
		self.setChannelEnable(3, False)
		self.setChannelEnable(4, False)

		self.setWaveformMode_Normal()
		self.setWaveformFormat_ASCII()

	def scpiCommand(self, command):
		self.s.sendall((command + "\n").encode())
		readData = ""
		while True:
			dataBlock = self.s.recv(4096*10)
			dataBlockStr = dataBlock.decode("utf-8")
			readData = readData + dataBlockStr

			if dataBlock[-1] == 10:
				break
		return readData

	def scpiCommand_NoReply(self, command):
		self.s.sendall((command+"\n").encode())
		return

	def setChannelEnable(self, channel, enabled):
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel has to be 1 to 4")

		if enabled:
			self.scpiCommand_NoReply(":CHAN{}:DISP ON".format(channel))
		else:
			self.scpiCommand_NoReply(":CHAN{}:DISP OFF".format(channel))

	def setTriggerSweep_Single(self):
		self.scpiCommand_NoReply(":TRIG:SWE SING")
	def setTriggerSweep_Auto(self):
		self.scpiCommand_NoReply(":TRIG:SWE AUTO")
	def setTriggerSweep_Normal(self):
		self.scpiCommand_NoReply(":TRIG:SWE NORM")

	def setWaveformMode_Normal(self):
		self.scpiCommand_NoReply(":WAV:MODE NORM")
	def setWaveformMode_Raw(self):
		self.scpiCommand_NoReply(":WAV:MODE RAW")

	def setWaveformFormat_ASCII(self):
		self.scpiCommand_NoReply(":WAV:FORM ASC")

	def setTimebasePerDivision(self, secondsPerDivision):
		if (secondsPerDivision > 50) or (secondsPerDivision < 5e-9):
			raise ValueError("Seconds per division has to be in range of 50s to 5 ns")
		self.scpiCommand_NoReply(f":TIM:SCAL {secondsPerDivision}")
	def setTimebaseModeMain(self):
		self.scpiCommand_NoReply(":TIM:MODE MAIN")

	def run(self):
		self.scpiCommand_NoReply(":RUN")
	def stop(self):
		self.scpiCommand_NoReply(":STOP")

	def waitTriggerDone(self):
		while(self.scpiCommand(":TRIG:STAT?") != "STOP"):
			pass
	def isTriggerDone(self):
		repl = self.scpiCommand(":TRIG:STAT?").strip()
		if repl == "WAIT":
			return False
		else:
			return True
	def setTriggerLevel(self, level):
		self.scpiCommand_NoReply(f":TRIG:EDGE:LEV {level}")

	def setTriggerSource(self, channel):
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel for trigger source has to be in range 1 - 4")
		self.scpiCommand_NoReply(":TRIG:MODE EDGE")
		self.scpiCommand_NoReply(f":TRIG:EDGE:SOUR CHAN{channel}")

	def setChannelOffset(self, channel, offset):
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel for trigger source has to be in range 1 - 4")
		self.scpiCommand_NoReply(f":CHAN{channel}:OFFS {offset}")
	def setChannelScale(self, channel, perdivision):
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel has to be in range 1 - 4")
		if (perdivision < 10e-3) or (perdivision > 100):
			raise ValueError("Out of range")
		self.scpiCommand_NoReply(f":CHAN{channel}:SCAL {perdivision}")

	def setCounterEnabled(self, enable):
		if enable:
			self.scpiCommand_NoReply(":COUN:ENAB ON")
		else:
			self.scpiCommand_NoReply(":COUN:ENAB OFF")
	def setCounterChannel(self, channel):
		channel = int(channel)
		if (channel < 1) or (channel > 4):
			raise ValueError("Channel has to be in range 1 - 4")
		self.scpiCommand_NoReply(f":COUN:SOUR CHAN{channel}")
	def setCounterMode(self, mode):
		if mode == "f":
			mode = "FREQ"
		elif mode == "t":
			mode = "PER"
		else:
			raise ValueError("Mode has to be (f)requency or (t)ime")
		self.scpiCommand_NoReply(f":COUN:MODE {mode}")
	def queryCounter(self):
		data = self.scpiCommand(":COUN:CURR?")
		return float(data)

	def queryData(self, channel):
		if isinstance(channel, list) or isinstance(channel, tuple):
			res = {
				'payload' : 'data'
			}
			for chan in channel:
				res[chan] = self.queryData(chan)
			return res

		if (channel < 1) or (channel > 4):
			raise ValueError("Invalid channel number (1-4 valid)")

		self.scpiCommand_NoReply(":WAV:SOUR CHAN{}".format(channel))
		data = self.scpiCommand(":WAV:DATA?")
		if data[0] != '#':
			return False
		headersym = data[0]
		headerlen = int(data[1])
		symcount = data[2:2+headerlen]
		data = data[2+headerlen:].split(",")
		for i in range(len(data)-1):
			data[i] = float(data[i])
		del data[len(data)-1]

		return np.asarray(data)

class SpeedOfLightDAQ:
	def __init__(self, queueDAQtoGUI, queueGUItoDAQ, defaultLoglevel = logging.DEBUG):
		self._queueDAQtoGUI = queueDAQtoGUI
		self._queueGUItoDAQ = queueGUItoDAQ

		self._logger = logging.getLogger(__name__)
		self._logger.addHandler(logging.StreamHandler())
		self._logger.setLevel(defaultLoglevel)

		# Read configuration file ...
		self._cfg = self._readConfigurationFile()
		if not self._cfg:
			# We send our termination signal to the main process
			queueDAQtoGUI.put(None)
			return

		if "loglevel" in self._cfg:
			# ToDo
			pass

		# Read our configuration and open oscilloscope connection
		if not "osci" in self._cfg:
			self._logger.error("[DAQ] No oscilloscope connection specified for DAQ")
		if not ("ip" in self._cfg['osci']):
			self._logger.error("[DAQ] Missing IP specification for oscilloscope in DAQ configuration")

		if ("osci" in self._cfg) and ("ip" in self._cfg['osci']):
			osci_ip = self._cfg['osci']['ip']
		else:
			osci_ip = "10.0.0.196"

		# Create Oscilloscope isntance and try to connect ..
		try:
			self._osci = MSO5000Oscilloscope(osci_ip)
		except Exception as e:
			self._osci = MSO5000Oscilloscope_Simulation(logger = self._logger)
			self._logger.error(f"[DAQ] {e}")

		self._totalSampleTime = None
		self._maxQueryRate = None
		self._maxQueryPeriod = None

		if ("osci" in self._cfg) and ("sperdiv" in self._cfg["osci"]):
			self._totalSampleTime = float(self._cfg["osci"]["sperdiv"]) * 10.0
			self._osci.setTimebaseModeMain()
			self._osci.setTimebasePerDivision(self._cfg["osci"]["sperdiv"])

		if ("osci" in self._cfg) and ("trigch" in self._cfg["osci"]):
			self._osci.setTriggerSource(self._cfg["osci"]["trigch"])
			if ("osci" in self._cfg) and ("triglvl" in self._cfg["osci"]):
				self._osci.setTriggerLevel(self._cfg["osci"]["triglvl"])

		if "osci" in self._cfg:
			if "ch1" in self._cfg['osci']:
				if "offset" in self._cfg['osci']['ch1']:
					self._osci.setChannelOffset(1, self._cfg['osci']['ch1']['offset'])
				if "scale" in self._cfg['osci']['ch1']:
					self._osci.setChannelScale(1, self._cfg['osci']['ch1']['scale'])
			if "ch2" in self._cfg['osci']:
				if "offset" in self._cfg['osci']['ch2']:
					self._osci.setChannelOffset(2, self._cfg['osci']['ch2']['offset'])
				if "scale" in self._cfg['osci']['ch2']:
					self._osci.setChannelScale(2, self._cfg['osci']['ch2']['scale'])
			if "maxqueryrate" in self._cfg['osci']:
				self._maxQueryRate = float(self._cfg['osci']['maxqueryrate'])
				self._maxQueryPeriod = 1.0 / float(self._cfg['osci']['maxqueryrate'])

		self._chopperDiameter = None
		self._chopperCircumference = None

		if "chopper" in self._cfg:
			if "diameter" in self._cfg['chopper']:
				self._chopperDiameter = self._cfg['chopper']['diameter']
				self._chopperCircumference = self._chopperDiameter * math.pi

		self._pathlen = 100
		self._pathn = 1

		if "path" in self._cfg:
			if "length" in self._cfg["path"]:
				self._pathlen = self._cfg["path"]["length"]
			if "n" in self._cfg["path"]:
				self._pathn = self._cfg["path"]["n"]

		self._osci.setCounterEnabled(True)
		self._osci.setCounterChannel(1)
		self._osci.setCounterMode('f')

	def run(self):
		# Run one measurement after each other ...
		if not (("mode" in self._cfg) and (self._cfg["mode"] == "triggered")):
			# Execute run command once when we are not in triggered mode
			self._osci.run()

		lastQuery = datetime.datetime.now()
		while True:
			if self._maxQueryPeriod is not None:
				if (datetime.datetime.now() - lastQuery).total_seconds() < self._maxQueryPeriod:
					continue
			lastQuery = datetime.datetime.now()

			# Depends on configuration if we are running in triggered
			# or in continuous mode
			if ("mode" in self._cfg) and (self._cfg["mode"] == "triggered"):
				self._osci.setTriggerSweep_Single()
				while not self._osci.isTriggerDone():
					pass
				self._logger.debug("[DAQ] Triggered")
			else:
				self._osci.setTriggerSweep_Normal()

			data = self._osci.queryData((1,2))
			if len(data[1]) != len(data[2]):
				self._logger.debug("[DAQ] Dropping samples due to different trace widths")
				continue

			if self._chopperCircumference is not None:
				data['velocity'] = (self._chopperCircumference * self._osci.queryCounter())
			else:
				data['velocity'] = self._osci.queryCounter()

			data['path'] = {
				'len' : self._pathlen,
				'n' : self._pathn
			}

			data['t'] = np.linspace(0, self._totalSampleTime, len(data[1]))
			try:
				#Wait for empty queue ...
				self._queueDAQtoGUI.join()
				self._queueDAQtoGUI.put(data, block = False)
			except:
				self._logger.debug("[DAQ] Dropping measurement due to full queue")

			try:
				newItem = self._queueGUItoDAQ.get(block = False)
				if newItem is None:
					self._logger.debug("[DAQ] Got termination notification from GUI, terminating")
					self._queueGUItoDAQ.task_done()
					break

				self._queueGUItoDAQ.task_done()
			except queue.Empty:
				pass

		self._queueDAQtoGUI.put(None)

	def _readConfigurationFile(self):
		cfgPath = os.path.join(Path.home(), ".config/speedoflight/daq.conf")
		self._logger.debug(f"[DAQ] Trying to load DAQ configuration from {cfgPath}")
		cfg = None

		try:
			with open(cfgPath) as cfgFile:
				cfg = json.load(cfgFile)
		except FileNotFoundError:
			self._logger.error(f"[DAQ] Failed to open configuration file {cfgPath}")
			return False
		except JSONDecodeError as e:
			self._logger.error(f"[DAQ] Failed to read configuration file {cfgPath}: {e}")
			return False

		return cfg
