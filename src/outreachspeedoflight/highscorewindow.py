from tkinter import *
import tkinter as Tk
import PySimpleGUI as sg
sg.change_look_and_feel('DarkAmber')

import numpy as np

import multiprocessing as mp

import json
import logging
import time
from time import sleep
from os.path import exists

import queue

import csv

from datetime import datetime

from outreachspeedoflight.strings import strings

class HighScoreWindow:
	def _createWindow(self):
		self._highscoreHeadings = [
			strings[self._lang]['start_time'],
			strings[self._lang]['end_time'],
			strings[self._lang]['name'],
			strings[self._lang]['velocity_max'],
			strings[self._lang]['velocity_avg'],
			strings[self._lang]['best_speed_of_light'],
			strings[self._lang]['best_deviation'],
			strings[self._lang]['stat_average_speed_of_light'],
			strings[self._lang]['errordeviation']
		]

		tmpHighScore = []
		if isinstance(self._highscore, list) and len(self._highscore) > 0:
			tmpHighScore = self._highscore_to_list(self._highscore)

		tablesize = (1350, 1400)
		if "tablesize" in self._cfg:
			if ("x" in self._cfg["tablesize"]) and ("y" in self._cfg["tablesize"]):
				tablesize = (int(self._cfg["tablesize"]['x']), int(self._cfg["tablesize"]['y']))

		layout = [
			[ sg.Text(strings[self._lang]['bestestimatestitle']) ],

			[
				sg.Column([
					[
						sg.Column([
							[ sg.Text(f"{strings[self._lang]['name']}:") ],
							[ sg.Text(f"{strings[self._lang]['maxspeed']}:") ],
							[ sg.Text(f"{strings[self._lang]['avgspeed']}:") ],

							[ sg.Text(f"{strings[self._lang]['bestmeasurement']}:") ],
							[ sg.Text(f"{strings[self._lang]['bestdeviation']}:") ],

							[ sg.Text(f"{strings[self._lang]['averagemeasurement']}:") ],
							[ sg.Text(f"{strings[self._lang]['averagedeviation']}:") ],

							[ sg.Button(strings[self._lang]['start'], key="btnStartStop") ],
							[ sg.Button(strings[self._lang]['abort'], key="btnAbort") ]
						], vertical_alignment='t'),
						sg.Column([
							[ sg.InputText(key="txtName") ],
							[ sg.Text("000", key="txtVelocityMax") ],
							[ sg.Text("000", key="txtVelocityAvg") ],

							[ sg.Text("000", key="txtMeasBest") ],
							[ sg.Text("000", key="txtMeasBestDeviation") ],

							[ sg.Text("000", key="txtMeasAvg") ],
							[ sg.Text("000", key="txtMeasDev") ]
						], vertical_alignment='t'),
						sg.Column([
							[ sg.Text(" ") ],
							[ sg.Text("km/h") ],
							[ sg.Text("km/h") ],

							[ sg.Text("m/s") ],
							[ sg.Text("%") ],

							[ sg.Text("m/s") ],
							[ sg.Text("m/s") ]
						], vertical_alignment='t')
					]
				], vertical_alignment='t'),
				sg.Column([
					[ sg.Table(values=tmpHighScore, key = "tableHS", headings=self._highscoreHeadings, display_row_numbers=True, alternating_row_color='black', selected_row_colors='red on blue', vertical_scroll_only=False, size = tablesize) ]
				], vertical_alignment='t')
			]
		]
		windowMain = sg.Window(
			"Highscore",
			layout,
			size=self._mainwindowsize,
			location=(0,0),
			finalize=True,
			no_titlebar=False,
			grab_anywhere=True
		)
		return windowMain

	def __init__(self, cfgPath, queueGUItoHighscore, defaultLoglevel = logging.DEBUG):
		self._lang = "en"

		self._logger = logging.getLogger(__name__)
		self._logger.addHandler(logging.StreamHandler())
		self._logger.setLevel(defaultLoglevel)

		self._state = 0

		self._queueFromGUI = queueGUItoHighscore
		self._cfg = self._readConfigurationFile(cfgPath)
		if not self._cfg:
			self._logger.error(f"[HIGHSCORE] Failed to load configuration file {cfgPath}")
			return

		if "lang" in self._cfg:
			if self._cfg["lang"] in strings:
				self._lang = self._cfg["lang"]

		if "loglevel" in self._cfg:
			# ToDo
			pass

		self._vthreshold = 10
		if "vthreshold" in self._cfg:
			self._vthreshold = self._cfg["vthreshold"]

		if ("mainwindowsize" in self._cfg) and ("x" in self._cfg['mainwindowsize']) and ("y" in self._cfg['mainwindowsize']):
			self._mainwindowsize = (self._cfg['mainwindowsize']['x'], self._cfg['mainwindowsize']['y'])
		else:
			self._mainwindowsize = (1024, 800)


		self._highscore = []
		if "highscorefile" in self._cfg:
			self._highscore = self._loadHighscore(self._cfg['highscorefile'])

		self._reset_state()

	def _reset_state(self):
		self._current = {
			"dtstart" : None,
			"dtend"   : None,
			"name"    : None,
			"vmax"    : None,
			"vavg"    : None,
			"cbest"   : None,
			"pctbest" : None,
			"cavg"    : None,
			"cstd"    : None,

			"measurements_v" : [],
			"measurements_c" : []
		}

	def _loadHighscore(self, filename):
		if not exists(filename):
			return []

		all = []
		with open(filename) as csvfile:
			reader = csv.reader(csvfile, delimiter=",", quotechar='"')
			for row in reader:
				newElem = {
					"name" : row[0],
					"vmax" : row[1],
					"vavg" : row[2],
					"cbest" : row[3],
					"pctbest" : row[4],
					"cavg" : row[5],
					"cstd" : row[6],
					"dtstart" : row[7],
					"dtend" : row[8]
				}
				all.append(newElem)
		return all

	def _storeHighscore(self, filename, data):
		with open(filename, 'w', newline='') as csvfile:
			writer = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
			for ent in data:
				writer.writerow([
					ent['name'],
					ent['vmax'],
					ent['vavg'],
					ent['cbest'],
					ent['pctbest'],
					ent['cavg'],
					ent['cstd'],
					ent['dtstart'],
					ent['dtend']
				])

	def _highscore_to_list(self, hs):
		tmpHighScore = []
		for ent in hs:
			tmpHighScore.append([
				ent['dtstart'],
				ent['dtend'],
				ent['name'],
				"{} km/h".format(round(float(ent['vmax']) * 3.6, 2)),
				"{} km/h".format(round(float(ent['vavg']) * 3.6, 2)),
				"{:0.3e} m/s".format(float(ent['cbest'])),
				"{} %".format(round(float(ent['pctbest']), 4)),
				"{:0.3e} m/s".format(float(ent['cavg'])),
				"{:0.3e} m/s".format(float(ent['cstd']))
			])
		return tmpHighScore

	def _current_to_highscore(self):
		if (self._current['name'] is not None) and (self._current['vmax'] is not None) and (self._current['vavg'] is not None)  and (self._current['cbest'] is not None) and (self._current['pctbest'] is not None) and (self._current['cavg'] is not None) and (self._current['cstd'] is not None):
			self._highscore.append(
				{
					"name" : self._current['name'],
					"vmax" : self._current['vmax'],
					"vavg" : self._current['vavg'],
					"cbest" : self._current['cbest'],
					"pctbest" : self._current['pctbest'],
					"cavg" : self._current['cavg'],
					"cstd" : self._current['cstd'],
					"dtstart" : self._current['dtstart'],
					"dtend" : self._current['dtend']
				}
			)

			self._highscore.sort(reverse = False, key = lambda e : str(e['pctbest']))

			if "highscorefile" in self._cfg:
				tmpHighScore = self._highscore_to_list(self._highscore)

				self._windowMain['tableHS'].update(tmpHighScore)
				self._storeHighscore(self._cfg['highscorefile'], self._highscore)

	def _update_stateUI(self):
		try:
			if self._current['vmax'] is not None:
				self._windowMain['txtVelocityMax'].update(round(self._current['vmax'] * 3.6, 2))
			else:
				self._windowMain['txtVelocityMax'].update("")
		except:
			self._windowMain['txtVelocityMax'].update("")

		try:
			if self._current['vavg'] is not None:
				self._windowMain['txtVelocityAvg'].update(round((self._current['vavg'])*3.6, 2))
			else:
				self._windowMain['txtVelocityAvg'].update("")
		except:
			self._windowMain['txtVelocityAvg'].update("")

		try:
			if self._current['cbest'] is not None:
				self._windowMain['txtMeasBest'].update("{:0.3e}".format(self._current['cbest']))
			else:
				self._windowMain['txtMeasBest'].update("")
		except:
			self._windowMain['txtMeasBest'].update("")

		try:
			if self._current['pctbest'] is not None:
				self._windowMain['txtMeasBestDeviation'].update(round(self._current['pctbest'], 3))
			else:
				self._windowMain['txtMeasBestDeviation'].update("")
		except:
			self._windowMain['txtMeasBestDeviation'].update("")

		try:
			if self._current['cavg'] is not None:
				self._windowMain['txtMeasAvg'].update("{:0.3e}".format(self._current['cavg']))
				self._windowMain['txtMeasDev'].update("{:0.3e}".format(self._current['cstd']))
			else:
				self._windowMain['txtMeasAvg'].update("")
				self._windowMain['txtMeasDev'].update("")
		except:
			self._windowMain['txtMeasAvg'].update("")
			self._windowMain['txtMeasDev'].update("")

	def _readConfigurationFile(self, cfgPath):
		self._logger.debug(f"[HIGHSCORE] Trying to load highscore configuration from {cfgPath}")
		cfg = None

		try:
			with open(cfgPath) as cfgFile:
				cfg = json.load(cfgFile)
		except FileNotFoundError:
			self._logger.error(f"[HIGHSCORE] Failed to open configuration file {cfgPath}")
			return False
		except json.JSONDecodeError as e:
			self._logger.error(f"[HIGHSCORE] Failed to read configuration file {cfgPath}: {e}")
			return False

		return cfg

	def run(self):
		self._windowMain = self._createWindow()
		while True:
			event, values = self._windowMain.read(timeout = 10)
			if event in ('btnExit', None, sg.WIN_CLOSED):
				self._logger.debug("[HIGHSCORE] terminated")
				if event == sg.WIN_CLOSED:
					sleep(5)
					break
			if event == "btnStartStop":
				if self._state == 0:
					# Start request
					self._reset_state()
					self._current['name'] = values['txtName']
					self._current['dtstart'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
					self._state = 1
					self._windowMain['btnStartStop'].update(strings[self._lang]['stop'])
					self._windowMain['txtName'].update(disabled=True)
					pass
				elif self._state == 1:
					self._state = 0
					self._current['dtend'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
					self._current_to_highscore()
					self._reset_state()
					self._windowMain['btnStartStop'].update(strings[self._lang]['start'])
					self._windowMain['txtName'].update(disabled=False)


					pass
			if event == "btnAbort":
				self._state = 0
				self._reset_state()
				self._windowMain['btnStartStop'].update(strings[self._lang]['start'])
				self._windowMain['txtName'].update(disabled=False)


			try:
				newItem = self._queueFromGUI.get(block = False)
				if newItem is None:
					self._logger.debug("[HIGHSCORE] Got termination request from GUI, terminating")
					self._queueFromGUI.task_done()
					# Termiantion request
					break

				# We've received an update. If speed is above threshold add to current
				# run if one's running
				if self._state == 1:
					if (newItem['velocity'] * 3.6) > self._vthreshold:
						# Our measurement is above threshold, we use it
						if (self._current['vmax'] is None) or (newItem['velocity'] > self._current['vmax']):
							if newItem['velocity'] < 1e5:
								self._current['vmax'] = newItem['velocity']
						self._current['measurements_v'].append(newItem['velocity'])

						# Check if our measurement is closer to the speed of ligth than bevore
						if (self._current['pctbest'] is None) or (newItem['speedOfLightDeviatePCT'] < self._current['pctbest']):
							self._current['pctbest'] = newItem['speedOfLightDeviatePCT']
							self._current['cbest'] = newItem['speedOfLightEstimate_Single']
						self._current['measurements_c'].append(newItem['speedOfLightEstimate_Single'])

						self._current['vavg'] =  (np.mean(self._current['measurements_v']))
						self._current['cavg'] =  (np.mean(self._current['measurements_c']))
						self._current['cstd'] =  (np.std(self._current['measurements_c']))

					self._update_stateUI()
			except queue.Empty:
				pass
