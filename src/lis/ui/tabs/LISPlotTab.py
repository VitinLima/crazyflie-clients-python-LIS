#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2023 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
#  02110-1301, USA.

"""
An example template for a tab in the Crazyflie Client. It comes pre-configured
with the necessary QT Signals to wrap Crazyflie API callbacks and also
connects the connected/disconnected callbacks.
"""

import logging
import threading
from datetime import datetime
import time
import csv
import sys
import os
import random

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox
import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import PyQt6.Qt6 as Qt6
import PyQt6.QtGui as QtGui
import PyQt6.QtQuick as QtQuick
from cfclient.ui.tab_toolbox import TabToolbox

from cflib.crazyflie.log import LogConfig
import cflib.crazyflie as crazyflie

import lis
from lis.__init__ import lis_backend
from .PyQtGraphCanvas import PlotTab, PlotCanvas

__author__ = 'Stagiaires au Laboratoir d\'Ingénierie de Systèmes de l\'École Nationale Supérieure d\'Ingénieurs de Caen'
__all__ = ['LISPlotTab']

logger = logging.getLogger(__name__)

plot_tab_class = uic.loadUiType(lis.module_path + "/ui/tabs/lisPlotTab.ui")[0]


class SimulationWorker(QtCore.QObject):
    # started = QtCore.pyqtSignal()
    # finished = QtCore.pyqtSignal()
    # progress = QtCore.pyqtSignal(int)
    simulate_logs = QtCore.pyqtSignal(int)

    def __init__(self, plottabs, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.plottabs = plottabs
        self.running = False
    
    def request_stop(self):
        self.running = False

    def run(self):
        print("Simulation Logging")
        self.running = True
        N = 0
        tic = time.time()
        while self.running:
            self.simulate_logs.emit(N)
            N += 1
            toc = tic + 0.01 - time.time()
            if toc < 0:
                print("Cant keep up: {},{}".format(toc, N))
                tic = time.time()
            else:
                tic += 0.01
                time.sleep(toc)

class LISPlotTab(TabToolbox, plot_tab_class):
    """Tab for plotting logging data"""

    _connected_signal = pyqtSignal(str)
    _disconnected_signal = pyqtSignal(str)
    _request_simulation_stop_signal = pyqtSignal()

    def __init__(self, helper):
        super(LISPlotTab, self).__init__(helper, 'LIS Plot')
        self.setupUi(self)
        self.backend = lis_backend
        self.setupSignals()
        
        self.running = False
        self.default_canvases = self.get_default_canvases()
        self.default_plots = self.get_default_plots()

        default_plots_tab = PlotTab(parent=self, fps_label=self.fpsLb)
        for config in self.default_canvases:
            canvas = default_plots_tab.add_new_canvas()
            canvas.setTitle(config['title'])
            canvas.setXLabel(config['xlabel'])
            canvas.setYLabel(config['ylabel'])

        for plot in self.default_plots:
            for variable in plot['variables']:
                default_plots_tab.add_new_log(loggroup=plot['key'], logvariable=variable, label=variable, canvas_id=plot['canvas_id'], scale=plot['scale'])
        self.tabs_widget.addTab(default_plots_tab, "Coordinates")
        self.tabs = [default_plots_tab]

        self.simulation_thread = QtCore.QThread()
        self.simulation_worker = SimulationWorker(self)

        self._request_simulation_stop_signal.connect(self.simulation_worker.request_stop)
        self.simulation_worker.simulate_logs.connect(self.simulate_logs)
        self.simulation_thread.started.connect(lambda: print("Thread started"))
        self.simulation_thread.finished.connect(lambda: print("Thread finished"))
        self.simulation_worker.moveToThread(self.simulation_thread)
        self.simulation_thread.started.connect(self.simulation_worker.run)

    def setupSignals(self):
        self._connected_signal.connect(self._connected)
        self._disconnected_signal.connect(self._disconnected)

        self._helper.cf.connected.add_callback(
            self._connected_signal.emit)
        self._helper.cf.disconnected.add_callback(
            self._disconnected_signal.emit)
        
        self.newtabBt.clicked.connect(self.on_new_tab)
    
    def on_new_tab(self):
        # newtab = PlotTab(parent=self)
        # self.tabs_widget.addTab(newtab, "New tab")
        # self.tabs += [newtab]
        if not self.running:
            self.running = True
            self.simulation_thread.start()
        else:
            self._request_simulation_stop_signal.emit()
            self.simulation_thread.terminate()
            self.simulation_thread.wait()
            self.running = False
    
    def simulate_logs(self, N):
        timestamp = N
        data = dict()
        for plot in self.default_plots:
            for var in plot['variables']:
                data[var] = random.random()
        for tab in self.tabs:
            for canvas in tab.canvas:
                for listener in canvas.listeners:
                    listener.callback(timestamp, data, None)

    def _connected(self, link_uri):
        self.lb_connectivity_state.setText("State: Connected")
    def _disconnected(self, link_uri):
        self.lb_connectivity_state.setText("State: Disconnected")
    
    def get_default_canvases(self):
        canvases = [
            dict(
                title='Position',
                xlabel='time [s],',
                ylabel='position [m]'),
            dict(
                title='Velocity',
                xlabel='time [s],',
                ylabel='velocity [m]'),
            dict(
                title='Acceleration',
                xlabel='time [s],',
                ylabel='acceleration [m]'),
            dict(
                title='Attitude',
                xlabel='time [s],',
                ylabel='angle [deg]'),
            dict(
                title='Attitude rate',
                xlabel='time [s],',
                ylabel='angle rate [deg/s]')
        ]
        return canvases
    
    def get_default_plots(self):
        plots = [
            dict(
                key='log_stateEstimatePos',
                name='State estimate position',
                variables={
                    'stateEstimate.x':'float',
                    'stateEstimate.y':'float',
                    'stateEstimate.z':'float'
                    },
                canvas_id=0,
                scale=1.0,
                ),
            dict(
                key='log_stateEstimateVel',
                name='State estimate velocity',
                variables={
                    'stateEstimate.vx':'float',
                    'stateEstimate.vy':'float',
                    'stateEstimate.vz':'float',
                    },
                canvas_id=1,
                scale=1.0,
                ),
            dict(
                key='log_stateEstimateAcc',
                name='State estimate acceleration',
                variables={
                    'stateEstimate.ax':'float',
                    'stateEstimate.ay':'float',
                    'stateEstimate.az':'float',
                    },
                canvas_id=2,
                scale=1.0,
                ),
            dict(
                key='log_stateEstimateAtt',
                name='State estimate attitude',
                variables={
                    'stateEstimate.yaw':'float',
                    'stateEstimate.pitch':'float',
                    'stateEstimate.roll':'float',
                    },
                canvas_id=3,
                scale=1.0,
                ),
            dict(
                key='log_stateEstimateAttRate',
                name='State estimate attitude rate',
                variables={
                    'stateEstimateZ.rateYaw':'int16_t',
                    'stateEstimateZ.ratePitch':'int16_t',
                    'stateEstimateZ.rateRoll':'int16_t',
                    },
                canvas_id=4,
                scale=1.0,
                ),
            dict(
                key='log_ctrltargetZPosVelAcc',
                name='Target pos',
                variables={
                    'ctrltargetZ.x':'int16_t',
                    'ctrltargetZ.y':'int16_t',
                    'ctrltargetZ.z':'int16_t',
                    },
                canvas_id=0,
                scale=1.0/1000.0,
                ),
            dict(
                key='log_ctrltargetZPosVelAcc',
                name='Target vel',
                variables={
                    'ctrltargetZ.vx':'int16_t',
                    'ctrltargetZ.vy':'int16_t',
                    'ctrltargetZ.vz':'int16_t',
                    },
                canvas_id=1,
                scale=1.0/1000.0,
                ),
            dict(
                key='log_ctrltargetZPosVelAcc',
                name='Target acc',
                variables={
                    'ctrltargetZ.ax':'int16_t',
                    'ctrltargetZ.ay':'int16_t',
                    'ctrltargetZ.az':'int16_t',
                    },
                canvas_id=2,
                scale=1.0/1000.0,
                ),
            dict(
                key='log_ctrltargetAtt',
                name='Target pitch and roll',
                variables={
                    'ctrltarget.pitch':'float',
                    'ctrltarget.roll':'float',
                    },
                canvas_id=3,
                scale=1.0,
                ),
            dict(
                key='log_ctrltargetAtt',
                name='Target yaw rate',
                variables={
                    'ctrltarget.yaw':'float',
                    },
                canvas_id=4,
                scale=1.0,
                ),
            ]
        return plots