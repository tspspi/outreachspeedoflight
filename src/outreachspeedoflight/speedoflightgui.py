from tkinter import *
import tkinter as Tk
import PySimpleGUI as sg
sg.change_look_and_feel('DarkAmber')

import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure

import multiprocessing as mp

import json
import logging
import time
from time import sleep

import queue

import os
from pathlib import Path

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})

from lmfit import Model
from lmfit.models import GaussianModel, ConstantModel

from PIL import Image
import io

# Import our own modules
from outreachspeedoflight.daq import SpeedOfLightDAQ
from outreachspeedoflight.highscorewindow import HighScoreWindow
from outreachspeedoflight.strings import strings

class SpeedOfLightGUI:
	def __init__(self, queueDAQtoGUI, queueGUItoDAQ, queueGUItoHIGHSCORE, defaultLoglevel = logging.DEBUG):
		self._logger = logging.getLogger(__name__)
		self._logger.addHandler(logging.StreamHandler())
		self._logger.setLevel(defaultLoglevel)

		self._lang = "en"

		self._queueDAQtoGUI = queueDAQtoGUI
		self._queueGUItoDAQ = queueGUItoDAQ
		self._queueGUItoHIGHSCORE = queueGUItoHIGHSCORE

		self._cfg = self._readConfigurationFile()
		if not self._cfg:
			# We send our termination signal to the DAQ process so it will terminate
			# and we can abort in a clean fashion after we received the confirmation
			queueGUItoDAQ.put(None)
			return

		if "loglevel" in self._cfg:
			# ToDo
			pass

		if "lang" in self._cfg:
			if self._cfg["lang"] in strings:
				self._lang = self._cfg["lang"]

		if "lastsamples" in self._cfg:
			self._lastEstimatesCount = self._cfg["lastsamples"]
		else:
			self._lastEstimatesCount = 32

		if "averagecount" in self._cfg:
			self._averageSamples = self._cfg["averagecount"]
		else:
			self._averageSamples = 32

		self._lastChopperSpeeds = np.zeros((self._lastEstimatesCount,))
		self._lastEstimates = np.zeros((self._lastEstimatesCount,))
		self._lastEstimatesC = np.zeros((self._lastEstimatesCount,))
		self._lastDeviatePercent = np.zeros((self._lastEstimatesCount,))
		self._lastEstimatesAvgC = np.zeros((self._lastEstimatesCount,))
		self._lastEstimatesStdC = np.zeros((self._lastEstimatesCount,))
		self._averageBuffer = np.zeros((self._averageSamples,))
		self._averageBufferIdx = 0

		self._lastAverage = np.zeros((self._lastEstimatesCount,))
		self._lastError = np.zeros((self._lastEstimatesCount,))

		if ("plotsize" in self._cfg) and ("x" in self._cfg['plotsize']) and ("y" in self._cfg['plotsize']):
			self._plotsize = (self._cfg['plotsize']['x'], self._cfg['plotsize']['y'])
		else:
			self._plotsize = (320, 240)

		if ("mainwindowsize" in self._cfg) and ("x" in self._cfg['mainwindowsize']) and ("y" in self._cfg['mainwindowsize']):
			self._mainwindowsize = (self._cfg['mainwindowsize']['x'], self._cfg['mainwindowsize']['y'])
		else:
			self._mainwindowsize = (1024, 800)


		self._fontsize = 18
		if "textfontsize" in self._cfg:
			self._fontsize = self._cfg["textfontsize"]

		this_dir, this_filename = os.path.split(__file__)
		logo1 = os.path.join(this_dir, "logo01.png")
		logo2 = os.path.join(this_dir, "logo02.png")

		layout = [
			[
				sg.Column([
					[ sg.Canvas(size=self._plotsize, key='canvRawData') ],
					[ sg.Canvas(size=self._plotsize, key='canvRawDataDiff') ],
					[ sg.Canvas(size=self._plotsize, key='canvRawDataCorr') ]
				], vertical_alignment='t'),
				sg.Column([
					[ sg.Canvas(size=self._plotsize, key='canvLastAvg') ],
					[ sg.Canvas(size=self._plotsize, key='canvLastEstimates') ],
					[ sg.Canvas(size=self._plotsize, key='canvSpeedOfLight') ]
				], vertical_alignment='t'),
				sg.Column([
					[
						sg.Column([
							[ sg.Text(f"{strings[self._lang]['current_speed']}: ", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text(f"{strings[self._lang]['measured_delay']}: ", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text(f"{strings[self._lang]['average_delay']}: ", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text(f"{strings[self._lang]['speed_of_light']}: ", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text(f"{strings[self._lang]['speed_of_light_avg']}: ", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
							[ sg.Text(f"{strings[self._lang]['speed_of_light_err']}: ", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
							[ sg.Text(f"{strings[self._lang]['deviation_real_speed']}: ", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ]
						], vertical_alignment='t'),
						sg.Column([
							[ sg.Text("000000", key="txtCurV", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("000000", key="txtCurDelay", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("000000", key="txtAvgDelay", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("000000", key="txtCurC", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("000000", key="txtC", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("000000", key="txtCErr", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("000000", key="txtDeviation", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ]
						], vertical_alignment='t'),
						sg.Column([
							[ sg.Text("km/h", text_color="#E2F0CB", font=("Helvetica", self._fontsize))  ],
							[ sg.Text("s", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("s", text_color="#E2F0CB", font=("Helvetica", self._fontsize))  ],
							[ sg.Text("m/s", text_color="#E2F0CB", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("m/s", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("m/s", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
							[ sg.Text("%", text_color="#FFB7B2", font=("Helvetica", self._fontsize)) ],
						], vertical_alignment='t')
					],
					[
						sg.Column([
							[ sg.Canvas(size=self._plotsize, key='canvDeviatePercent') ],
							[ sg.Canvas(size=self._plotsize, key='canvSpeedOfLightAvg') ]
						], vertical_alignment='t'),
						sg.Column([
							[ sg.Canvas(size=self._plotsize, key='canvChopperSpeed') ],
							[ sg.Image(data=self._loadResizedImage(logo1, (self._plotsize[0], int(self._plotsize[1]/2))), size=(self._plotsize[0], int(self._plotsize[1]/2))) ],
							[ sg.Image(data=self._loadResizedImage(logo2, (self._plotsize[0], int(self._plotsize[1]/2))), size=(self._plotsize[0], int(self._plotsize[1]/2))) ]
						], vertical_alignment='t')
					]
				]),
			],
			[ sg.Button("Exit", key = "btnExit") ]
		]
		self._windowMain = sg.Window(
			f"{strings[self._lang]['mainguititle']}",
			layout,
			size=self._mainwindowsize,
			location=(0,0),
			finalize=True,
			no_titlebar=False,
			grab_anywhere=True
		)


		self._figures = {
			'rawData' : self._init_figure('canvRawData', f"{strings[self._lang]['time']} [s]", f"{strings[self._lang]['signal']} [V]", f"{strings[self._lang]['captured_data_norm']}"),
			'rawDataDiff' : self._init_figure('canvRawDataDiff', f"{strings[self._lang]['time']} [s]", f"{strings[self._lang]['signal']} [V]", f"{strings[self._lang]['diffchannels']}", legend = False),
			'rawDataCorr' : self._init_figure('canvRawDataCorr', f"{strings[self._lang]['time']} [s]", f"{strings[self._lang]['correlation']}", f"{strings[self._lang]['correlation_function']}", legend = False),
			'lastAvg' : self._init_figure('canvLastAvg', f"{strings[self._lang]['measurements']}", f"{strings[self._lang]['delay']}", f"{strings[self._lang]['delayavg']}", legend = False),
			'lastEstimates' : self._init_figure('canvLastEstimates', f"{strings[self._lang]['measurements']}", f"{strings[self._lang]['delay']}", f"{strings[self._lang]['lastmeasurements']}", legend = False),
			'speedoflight' : self._init_figure('canvSpeedOfLight', f"{strings[self._lang]['measurements']}", f"{strings[self._lang]['speedoflight']} [m/s]", f"{strings[self._lang]['singlespeedoflightest']}", legend = False),

			'deviatePercent' : self._init_figure('canvDeviatePercent', f"{strings[self._lang]['measurements']}", f"{strings[self._lang]['deviation']} [%]", f"{strings[self._lang]['deviation_from_real_value']}", legend = False),
			'speedoflightavg' : self._init_figure('canvSpeedOfLightAvg', f"{strings[self._lang]['measurements']}", f"{strings[self._lang]['speedoflight']} [m/s]", f"{strings[self._lang]['averaged_speed_of_light']}", legend = False),
			'chopperspeed' : self._init_figure('canvChopperSpeed', f"{strings[self._lang]['measurements']}", f"{strings[self._lang]['chopperspeed']} [km/h]", f"{strings[self._lang]['chopperspeed']}", legend = False)
		}

		self._difffit_enable = False
		self._difffit_primary = False
		self._difffit_dump = False
		if "difffit" in self._cfg:
			if "enable" in self._cfg['difffit']:
				if self._cfg['difffit']['enable'] == "true":
					self._difffit_enable = True
			if "primary" in self._cfg['difffit']:
				if self._cfg['difffit']['primary'] == "true":
					self._difffit_primary = True
			if "dump" in self._cfg['difffit']:
				if self._cfg['difffit']['dump'] == "true":
					self._difffit_dump = True
		self._smooth_movingaverage_n = 0
		if "movingaverage" in self._cfg:
			self._smooth_movingaverage_n = int(self._cfg['movingaverage'])

	def _loadResizedImage(self, image, targetSize = None):
		if isinstance(image, str):
			image = Image.open(image)
		if targetSize is not None:
			image = image.resize(targetSize, Image.ANTIALIAS)

		bio = io.BytesIO()
		image.save(bio, format="PNG")
		return bio.getvalue()


	def _readConfigurationFile(self):
		cfgPath = os.path.join(Path.home(), ".config/speedoflight/gui.conf")
		self._logger.debug(f"[GUI] Trying to load DAQ configuration from {cfgPath}")
		cfg = None

		try:
			with open(cfgPath) as cfgFile:
				cfg = json.load(cfgFile)
		except FileNotFoundError:
			self._logger.error(f"[GUI] Failed to open configuration file {cfgPath}")
			return False
		except JSONDecodeError as e:
			self._logger.error(f"[GUI] Failed to read configuration file {cfgPath}: {e}")
			return False

		return cfg

	def _init_figure(self, canvasName, xlabel, ylabel, title, grid=True, legend=True):
		figTemp = Figure()
		fig = Figure(figsize = (self._plotsize[0] / figTemp.get_dpi(), self._plotsize[1] / figTemp.get_dpi()))
		self._figure_colors_fig(fig)

		ax = fig.add_subplot(111)

		self._figure_colors(ax)

		ax.set_xlabel(xlabel)
		ax.set_ylabel(ylabel)
		ax.set_title(title)

		if grid:
			ax.grid()
		fig_agg = FigureCanvasTkAgg(fig, self._windowMain[canvasName].TKCanvas)
		fig_agg.draw()
		fig_agg.get_tk_widget().pack(side='top', fill='both', expand=1)

		return {
			'figure' : fig,
			'axis' : ax,
			'fig_agg' : fig_agg,
			'xlabel' : xlabel,
			'ylabel' : ylabel,
			'title' : title,
			'grid' : grid,
			'legend' : legend
		}


	def _figure_colors_fig(self, fig):
		fig.set_facecolor((0,0,0))

	def _figure_colors(self, ax):
		ax.set_facecolor((0,0,0))
		ax.xaxis.label.set_color((0.77,0.80,0.92))
		ax.yaxis.label.set_color((0.77,0.80,0.92))
		ax.title.set_color((0.77,0.80,0.92))
		ax.spines['top'].set_color((0.77,0.80,0.92))
		ax.spines['bottom'].set_color((0.77,0.80,0.92))
		ax.spines['left'].set_color((0.77,0.80,0.92))
		ax.spines['right'].set_color((0.77,0.80,0.92))
		ax.tick_params(axis='x', colors=(0.77,0.80,0.92))
		ax.tick_params(axis='y', colors=(0.77,0.80,0.92))

	def _figure_begindraw(self, figname):
		self._figures[figname]['axis'].cla()
		self._figures[figname]['axis'].set_xlabel(self._figures[figname]['xlabel'])
		self._figures[figname]['axis'].set_ylabel(self._figures[figname]['ylabel'])
		self._figures[figname]['axis'].set_title(self._figures[figname]['title'])
		if self._figures[figname]['grid']:
			self._figures[figname]['axis'].grid()
		self._figure_colors(self._figures[figname]['axis'])
		return self._figures[figname]['axis']

	def _figure_enddraw(self, figname):
		if self._figures[figname]['legend']:
			self._figures[figname]['axis'].legend()
		self._figures[figname]['fig_agg'].draw()

	def _handleMeasurement(self, msg):
		# Normalize both traces and calculate differnce
		if (not 1 in msg) or (not 2 in msg):
			self._logger.warn("Not enough data in data message")
			return

		# Moving average ...
		if self._smooth_movingaverage_n > 0:
			msg[1] = np.convolve(msg[1], np.ones(self._smooth_movingaverage_n)/self._smooth_movingaverage_n, mode = 'valid')
			msg[2] = np.convolve(msg[2], np.ones(self._smooth_movingaverage_n)/self._smooth_movingaverage_n, mode = 'valid')

		if len(msg['t'] != len(msg[1])):
			msg['t'] = msg['t'][:len(msg[1])]

		# Normalize
		msg[1] = msg[1] - np.min(msg[1])
		msg[2] = msg[2] - np.min(msg[2])
		msg[1] /= np.max(msg[1])
		msg[2] /= np.max(msg[2])
		msg['diff'] = msg[1] - msg[2]

		# Make periodic signal for cross-correlation function calculation
		s1 = msg[1]
		s2 = msg[2]
		s1 = np.concatenate((s1, 1.0 - s1))
		s2 = np.concatenate((s2, 1.0 - s2))

		msg['correlation'] = np.correlate(s1, s2, "full")
		msg['correlationt'] = np.linspace(-2 * msg['t'][-1], 2 * msg['t'][-1], len(msg['correlation']))
		corrMaxIdx = np.argmax(msg['correlation'])
		corrMaxT = -1.0 * msg['correlationt'][corrMaxIdx]
		corrMaxVal = msg['correlation'][corrMaxIdx]
		corrMaxIdxShift = -1.0 * (corrMaxIdx - len(msg['correlation']) / 2)

		# Do fitting estimate
		if self._difffit_enable:
			peak = GaussianModel()
			offset = ConstantModel()
			model = peak + offset
			param = offset.make_params(c = np.median(msg['diff']))
			param += peak.guess(msg['diff'], x = msg['t'], amplitude = 0.5)
			result = model.fit(msg['diff'], param, x=msg['t'])
			if self._difffit_dump:
				print(result.fit_report())
			fitMaxT = result.params['fwhm'].value

		if self._difffit_enable and self._difffit_primary:
			maxT = fitMaxT
		else:
			maxT = corrMaxT

		#if corrMaxT < 0:
		#	corrMaxT = 0
		#	corrMaxVal = 0
		#	corrMaxIdxShift = 0

		# Insert into ringbuffer / append to "last" measurements
		self._lastEstimates = np.roll(self._lastEstimates, +1)
		self._lastEstimates[0] = maxT
		self._averageBuffer[self._averageBufferIdx] = maxT
		self._averageBufferIdx = (self._averageBufferIdx + 1) % len(self._averageBuffer)

		# Do averaging and error calculation
		self._lastAverage = np.roll(self._lastAverage, +1)
		self._lastError = np.roll(self._lastError, +1)
		currentAvgDelay = np.mean(self._averageBuffer)
		currentStdDelay = np.std(self._averageBuffer)
		self._lastAverage[0] = currentAvgDelay
		self._lastError[0] = currentStdDelay

		currentVelocity = msg['velocity']
		if currentVelocity > 1e8:
			currentVelocity = 0
		elif currentVelocity < 0:
			currentVelocity = 0

		if maxT != 0:
			newCurrentSpeedoflightEstimate = (msg['path']['len'] / maxT) * msg['path']['n']
			newAverageSpeedoflightEstimate = (msg['path']['len'] / currentAvgDelay) * msg['path']['n']
			newAverageSpeedoflightEstimateErr = (msg['path']['len'] / (currentAvgDelay * currentAvgDelay)) * currentStdDelay
			deviatePercent =  ((abs(abs(newAverageSpeedoflightEstimate)-299792458.0) / 299792458.0))*100.0
		else:
			newCurrentSpeedoflightEstimate = 0
			newAverageSpeedoflightEstimate = 0
			newAverageSpeedoflightEstimateErr = 0
			deviatePercent = 100

		msg['maxT'] = maxT
		msg['speedOfLightEstimate_Single'] = newCurrentSpeedoflightEstimate
		msg['speedOfLightEstimate_Average'] = newAverageSpeedoflightEstimate
		msg['speedOfLightEstimate_AvgDeviation'] = newAverageSpeedoflightEstimateErr
		msg['speedOfLightDeviatePCT'] = deviatePercent

		self._lastChopperSpeeds = np.roll(self._lastChopperSpeeds, +1)
		self._lastChopperSpeeds[0] = currentVelocity * 3.6

		# Update deviation and speed of light estimates
		self._lastEstimatesC = np.roll(self._lastEstimatesC, +1)
		self._lastEstimatesAvgC = np.roll(self._lastEstimatesAvgC, +1)
		self._lastEstimatesStdC = np.roll(self._lastEstimatesStdC, +1)
		self._lastDeviatePercent = np.roll(self._lastDeviatePercent, +1)
		self._lastEstimatesC[0] = newCurrentSpeedoflightEstimate
		self._lastEstimatesAvgC[0] = newAverageSpeedoflightEstimate
		self._lastEstimatesStdC[0] = newAverageSpeedoflightEstimateErr
		self._lastDeviatePercent[0] = deviatePercent

		self._windowMain['txtCurV'].update(round(currentVelocity * 3.6, 2))
		self._windowMain['txtCurDelay'].update("{:0.3e}".format(maxT))
		self._windowMain['txtAvgDelay'].update("{:0.3e}".format(currentAvgDelay))
		# self._windowMain['txtErrDelay'].update("{:0.3e}".format(currentStdDelay))
		self._windowMain['txtCurC'].update("{:0.3e}".format(abs(newCurrentSpeedoflightEstimate)))
		self._windowMain['txtC'].update("{:0.3e}".format(abs(newAverageSpeedoflightEstimate)))
		self._windowMain['txtCErr'].update("{:0.3e}".format(abs(newAverageSpeedoflightEstimateErr)))
		self._windowMain['txtDeviation'].update(str(round(deviatePercent, 3)))

		# Transmit information to our highscore window
		self._queueGUItoHIGHSCORE.put(msg, block = False)

		# Plot into our "raw" data frame ...
		ax = self._figure_begindraw('rawData')
		ax.plot(msg['t'], msg[1], label = 'Channel 1')
		ax.plot(msg['t'], msg[2], label = 'Channel 2')
		self._figure_enddraw('rawData')

		ax = self._figure_begindraw('rawDataDiff')
		ax.plot(msg['t'],msg['diff'], label = 'Difference')
		if self._difffit_enable:
			ax.plot(msg['t'], result.best_fit, color = 'red', linestyle = 'dashed', label = "Fitting Gaussian")
		self._figure_enddraw('rawDataDiff')

		ax = self._figure_begindraw('rawDataCorr')
		ax.plot(msg['correlationt'], msg['correlation'], label = 'Correlation')
		ax.plot(-1.0 * corrMaxT, corrMaxVal, label = 'Maximum', marker="o")
		self._figure_enddraw('rawDataCorr')

		ax = self._figure_begindraw('lastEstimates')
		ax.plot(self._lastEstimates, label = "Last estimates")
		self._figure_enddraw('lastEstimates')

		ax = self._figure_begindraw('lastAvg')
		ax.errorbar(range(len(self._lastAverage)), self._lastAverage, yerr = self._lastError, label = "Averaged results")
		self._figure_enddraw('lastAvg')

		ax = self._figure_begindraw('speedoflight')
		ax.plot(self._lastEstimatesC, label = "Last estimates")
		self._figure_enddraw('speedoflight')

		ax = self._figure_begindraw('speedoflightavg')
		ax.errorbar(range(len(self._lastEstimatesAvgC)), self._lastEstimatesAvgC, yerr = self._lastEstimatesStdC, label = "Averaged estimates")
		self._figure_enddraw('speedoflightavg')

		ax = self._figure_begindraw('deviatePercent')
		ax.plot(self._lastDeviatePercent, label = "Deviation in percent")
		self._figure_enddraw('deviatePercent')

		ax = self._figure_begindraw('chopperspeed')
		ax.plot(self._lastChopperSpeeds, label = "Chopper speed")
		self._figure_enddraw('chopperspeed')

	def runUI(self):
		while True:
			event, values = self._windowMain.read(timeout = 10)
			if event in ('btnExit', None, sg.WIN_CLOSED):
				self._logger.debug("[GUI] User requests termination, signalling to DAQ")
				self._queueGUItoDAQ.put(None)
				if event == sg.WIN_CLOSED:
					sleep(5)
					break

			try:
				newItem = self._queueDAQtoGUI.get(block = False)

				if newItem is None:
					# We got termination notification from the DAQ - we terminate
					# the GUI too
					self._logger.debug("[GUI] Got termination notification from DAQ, terminating")
					self._queueDAQtoGUI.task_done()
					break

				if isinstance(newItem, dict):
					if "payload" in newItem:
						if newItem['payload'] == "data":
							# We received a new measurement ...
							self._handleMeasurement(newItem)
						else:
							self._logger.warning(f"Unknown message type {newItem['payload']}")
					else:
						print(newItem)
						self._logger.warning(f"Unknown message type without type indicator")
				else:
					self._logger.warning("Received message is not a dictionary")

				# Signal this task has been done (joinable queue)
				self._queueDAQtoGUI.task_done()
			except queue.Empty:
				# We just do another iteration in this case ...
				pass


def mainStartup_DAQ(queueDAQtoGUI, queueGUItoDAQ):
	print("DAQ running", flush=True)
	daq = SpeedOfLightDAQ(queueDAQtoGUI, queueGUItoDAQ)
	daq.run()

def mainStartup_Highscore(highscoreCfgPath, queueGUItoHighscore):
	print("Highscore running", flush=True)
	hsw = HighScoreWindow(highscoreCfgPath, queueGUItoHighscore)
	hsw.run()

def mainStartup():
	# Check the configuration files are present
	guiCfgPath = os.path.join(Path.home(), ".config/speedoflight/gui.conf")
	if not os.path.exists(guiCfgPath):
		print(f"GUI configuration file missing at {guiCfgPath}")
		return
	daqCfgPath = os.path.join(Path.home(), ".config/speedoflight/daq.conf")
	if not os.path.exists(daqCfgPath):
		print(f"GUI configuration file missing at {daqCfgPath}")
		return
	highscoreCfgPath = os.path.join(Path.home(), ".config/speedoflight/highscore.conf")
	if not os.path.exists(highscoreCfgPath):
		print(f"Highscore configuration file missing at {highscoreCfgPath}")
		return
	
	# multictx = mp.get_context("fork")
	multictx = mp.get_context("spawn")
	queueDAQtoGUI = multictx.JoinableQueue()
	queueGUItoDAQ = multictx.JoinableQueue()
	queueGUItoHighscore = multictx.JoinableQueue()

	procDAQ = multictx.Process(target = mainStartup_DAQ, args = (queueDAQtoGUI, queueGUItoDAQ))
	procDAQ.start()
	procHighscore = multictx.Process(target = mainStartup_Highscore, args = (highscoreCfgPath, queueGUItoHighscore))
	procHighscore.start()

	gui = SpeedOfLightGUI(queueDAQtoGUI, queueGUItoDAQ, queueGUItoHighscore)
	gui.runUI()

if __name__ == "__main__":
	mainStartup()