from tkinter import *
import tkinter as Tk
import PySimpleGUI as sg

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure

import multiprocessing as mp

import json
import logging
import time

# Import our own modules
from daq import SpeedOfLightDAQ

class SpeedOfLightGUI:
	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._logger.addHandler(logging.StreamHandler())

def mainStartup_DAQ(queueDAQtoGUI, queueGUItoDAQ):
	print("DAQ running", flush=True)
	daq = SpeedOfLightDAQ(queueDAQtoGUI, queueGUItoDAQ)
	daq.run()

def mainStartup():
	multictx = mp.get_context("fork")
	queueDAQtoGUI = multictx.JoinableQueue()
	queueGUItoDAQ = multictx.JoinableQueue()

	procDAQ = multictx.Process(target = mainStartup_DAQ, args = (queueDAQtoGUI, queueGUItoDAQ))
	procDAQ.start()

	while True:
		newData = queueDAQtoGUI.get()
		queueDAQtoGUI.task_done()
		if newData is None:
			break
		print(newData)


if __name__ == "__main__":
	mainStartup()