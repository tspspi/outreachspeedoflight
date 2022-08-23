from time import sleep

import socket
import math

import numpy as np

# Debugging only
import matplotlib.pyplot as plt

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
		while(self.scpiCommand_NoReply(":TRIG:STAT?") != "STOP"):
			pass

	def queryData(self, channel):
		if isinstance(channel, list) or isinstance(channel, tuple):
			res = {}
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


if __name__ == "__main__":
	osci = MSO5000Oscilloscope()
	data = osci.queryData((1, 2))

	for ent in data:
		plt.plot(data[ent], label = f"Channel {ent}")
	plt.show()