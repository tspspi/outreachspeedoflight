from time import sleep
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

	def waitTriggerDone(self):
		while(self.scpiCommand(":TRIG:STAT?") != "STOP"):
			pass
	def isTriggerDone(self):
		repl = self.scpiCommand(":TRIG:STAT?").strip()
		if repl == "WAIT":
			return False
		else:
			return True

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

	def run(self):
		# Run one measurement after each other ...
		while True:
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
			self._queueDAQtoGUI.put(data)

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
