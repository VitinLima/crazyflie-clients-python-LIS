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

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QFileDialog

import lis
from cfclient.ui.tab_toolbox import TabToolbox

from cflib.crazyflie.log import LogConfig

from lis.__init__ import lis_backend

__author__ = 'Stagiaires au Laboratoir d\'Ingénierie de Systèmes de l\'École Nationale Supérieure d\'Ingénieurs de Caen'
__all__ = ['LISMainTab']

logger = logging.getLogger(__name__)

main_tab_class = uic.loadUiType(lis.module_path + "/ui/tabs/lisMainTab.ui")[0]


class LISMainTab(TabToolbox, main_tab_class):
    """Tab for plotting logging data"""

    _connected_signal = pyqtSignal(str)
    _disconnected_signal = pyqtSignal(str)
    _log_data_signal = pyqtSignal(int, object, object)
    _log_error_signal = pyqtSignal(object, str)
    _param_updated_signal = pyqtSignal(str, str)

    def __init__(self, helper):
        super(LISMainTab, self).__init__(helper, 'LIS Main')
        self.setupUi(self)
        self.backend = lis_backend
        self.setupSignals()
        self.backend.attach_cf(self._helper.cf)

        # self.backend.add_callback_to_default_log('log_stateEstimateAttRate', lambda timestamp, data, logconf: self.callback_stateEstimateAttRate(timestamp, data, logconf, key='log_stateEstimateAttRate'))
        self.backend.add_callback_to_log('log_stateEstimateAtt', lambda timestamp, data, logconf: self.callback_stateEstimateAtt(timestamp, data, logconf, key='log_stateEstimateAtt'))
        self.backend.add_callback_to_log('log_stateEstimateAcc', lambda timestamp, data, logconf: self.callback_stateEstimateAcc(timestamp, data, logconf, key='log_stateEstimateAcc'))
        self.backend.add_callback_to_log('log_stateEstimateVel', lambda timestamp, data, logconf: self.callback_stateEstimateVel(timestamp, data, logconf, key='log_stateEstimateVel'))
        self.backend.add_callback_to_log('log_stateEstimatePos', lambda timestamp, data, logconf: self.callback_stateEstimatePos(timestamp, data, logconf, key='log_stateEstimatePos'))
    
    def setupSignals(self):
        # Always wrap callbacks from Crazyflie API though QT Signal/Slots
        # to avoid manipulating the UI when rendering it
        self._connected_signal.connect(self._connected)
        self._disconnected_signal.connect(self._disconnected)
        self._log_data_signal.connect(self._log_data_received)
        self._param_updated_signal.connect(self._param_updated)

        # Connect the Crazyflie API callbacks to the signals
        self._helper.cf.connected.add_callback(
            self._connected_signal.emit)
        self._helper.cf.disconnected.add_callback(
            self._disconnected_signal.emit)

        self.startBt.clicked.connect(self.backend.on_start)
        self.landBt.clicked.connect(self.backend.on_land)
        self.emergencyStopBt.clicked.connect(self.backend.on_emergency_stop)
        self.unlockBt.clicked.connect(self.backend.on_unlock)
        self.systemResetBt.clicked.connect(self.backend.on_system_reset)
        self.greetingsBt.clicked.connect(self.backend.on_greetings)
        self.loggingBt.clicked.connect(self.on_logging_bt)
        self.searchBt.clicked.connect(self.on_search)
        
        self.is_logging = False

        self.logging_data = []
        self.loggingLe.setText(os.path.join(os.getcwd(), "position_log.csv"))
    
    def on_logging_bt(self):
        if self.loggingBt.getText()=="Start logging":
            self.is_logging = True
            self.loggingBt.setText("Stop logging")
        else:
            self.is_logging = False
            self.save_to_csv()
            self.loggingBt.setText("Start logging")
    
    def on_search(self):
        curfilename = self.loggingLe.text()
        filename = QFileDialog.getSaveFileName(self, "Save log data as:", curfilename, ".csv files")
        if len(filename[0]) > 0:
            self.loggingLe.setText(filename[0])
        
    def save_to_csv(self):
        filename = self.loggingLe.getText()
        with open(filename, mode='w', newline='') as csvfile:
            fieldnames = ['timestamp', 'x', 'y', 'z']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.logging_data:
                writer.writerow(row)
        print(f"Données sauvegardées dans {filename}")

    def callback_stateEstimatePos(self, timestamp, data, logconf, key=''):
        x = data['stateEstimate.x']
        y = data['stateEstimate.y']
        z = data['stateEstimate.z']
        self.positionLb.setText("Position: ({:.2f},{:.2f},{:.2f}) [m]".format(x,y,z))
        # Sauvegarde dans le fichier CSV
        if self.is_logging:
            self.logs_configs[key].append({
                'timestamp': timestamp,
                'x': x,
                'y': y,
                'z': z
            })


    def callback_stateEstimateVel(self, timestamp, data, logconf, key=''):
        vx = data['stateEstimate.vx']
        vy = data['stateEstimate.vy']
        vz = data['stateEstimate.vz']
        self.vxLb.setText("X: {:.2f} [m/s]".format(vx))
        self.vyLb.setText("Y: {:.2f} [m/s]".format(vy))
        self.vzLb.setText("Z: {:.2f} [m/s]".format(vz))
        # Sauvegarde dans le fichier CSV
        if self.is_logging:
            self.logs_configs[key].append({
                'timestamp': timestamp,
                'vx': vx,
                'vy': vy,
                'vz': vz
            })

    def callback_stateEstimateAcc(self, timestamp, data, logconf, key=''):
        ax = data['stateEstimate.ax']
        ay = data['stateEstimate.ay']
        az = data['stateEstimate.az']
        self.axLb.setText("X: {:.2f} [m/s²]".format(ax))
        self.ayLb.setText("Y: {:.2f} [m/s²]".format(ay))
        self.azLb.setText("Z: {:.2f} [m/s²]".format(az))
        # Sauvegarde dans le fichier CSV
        if self.is_logging:
            self.logs_configs[key].append({
                'timestamp': timestamp,
                'ax': ax,
                'ay': ay,
                'az': az
            })

    def callback_stateEstimateAtt(self, timestamp, data, logconf, key=''):
        yaw = data['stateEstimate.yaw']
        pitch = data['stateEstimate.pitch']
        roll = data['stateEstimate.roll']
        self.yawLb.setText("Yaw: {:.2f} [deg]".format(yaw))
        self.pitchLb.setText("Pitch: {:.2f} [deg]".format(pitch))
        self.rollLb.setText("Roll: {:.2f} [deg]".format(roll))
        # Sauvegarde dans le fichier CSV
        if self.is_logging:
            self.logs_configs[key].append({
                'timestamp': timestamp,
                'yaw': yaw,
                'pitch': pitch,
                'roll': roll
            })

    def callback_stateEstimateAttRate(self, timestamp, data, logconf, key=''):
        # yawrate = data['stateEstimateZ.rateYaw']*1000.0
        # pitchrate = data['stateEstimateZ.ratePitch']*1000.0
        # rollrate = data['stateEstimateZ.rateRoll']*1000.0
        # self.yawRateLb.setText("{:.2f}".format(yawrate))
        # self.pitchRateLb.setText("{:.2f}".format(pitchrate))
        # self.rollRateLb.setText("{:.2f}".format(rollrate))
        # # Sauvegarde dans le fichier CSV
        # if self.is_logging:
        #     self.logs_configs[key].append({
        #         'timestamp': timestamp,
        #         'yawrate': yawrate,
        #         'pitchrate': pitchrate,
        #         'rollrate': rollrate
        #     })
        pass

    def _connected(self, link_uri):
        """Callback when the Crazyflie has been connected"""
        # logger.debug("Crazyflie connected to {}".format(link_uri))
        self.lb_connectivity_state.setText("State: Connected")
        # self.startLogs()

    def _disconnected(self, link_uri):
        """Callback for when the Crazyflie has been disconnected"""
        # logger.debug("Crazyflie disconnected from {}".format(link_uri))
        self.lb_connectivity_state.setText("State: Disconnected")
        # self.stopLogs()

    def _param_updated(self, name, value):
        """Callback when the registered parameter get's updated"""
        # logger.debug("Updated {0} to {1}".format(name, value))

    def _log_data_received(self, timestamp, data, log_conf):
        """Callback when the log layer receives new data"""
        # logger.debug("{0}:{1}:{2}".format(timestamp, log_conf.name, data))

    def _logging_error(self, log_conf, msg):
        """Callback from the log layer when an error occurs"""
        # QMessageBox.about(self, "Example error",
        #                   "Error when using log config"
        #                   " [{0}]: {1}".format(log_conf.name, msg))
