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
A (mostly) robust implementation of an autopilot system in the Applayer of the Crazyflie,
allowing for the use of both low level commander layer (direct PID setting) and the
high level commander and allowing the choice of Controller to use, being thus changed
dynamically in mid-flight using the Param lib.
"""

import logging
import threading
from datetime import datetime
import time
import csv
import sys
import os
import re

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QListView
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QModelIndex

import lis
from cfclient.ui.tab_toolbox import TabToolbox

from cflib.crazyflie.log import LogConfig

from lis.__init__ import lis_backend
from lis.Waypoint import *

from lis import Protocol

__author__ = 'Stagiaires au Laboratoir d\'Ingénierie des Systèmes de l\'École Nationale Supérieure d\'Ingénieurs de Caen'
__all__ = ['LISAutoPilotTab']

logger = logging.getLogger(__name__)

command_tab_class = uic.loadUiType(lis.module_path + "/ui/tabs/lisAutoPilotTab.ui")[0]

class LISAutoPilotTab(TabToolbox, command_tab_class):
    """Tab for commanding the drone with autopilot"""

    _connected_signal = pyqtSignal(str)
    _disconnected_signal = pyqtSignal(str)

    def __init__(self, helper):
        super(LISAutoPilotTab, self).__init__(helper, 'LIS Command')
        self.setupUi(self)
        self.backend = lis_backend
        self.logs_configs = dict()
        self.running_logs = []
        self.waypoints = []
        self.waypoint_items = []
        self.setupSignals()
        self.waypoints_container: QListView
        self.waypoints_listmodel = QStandardItemModel(self.waypoints_container)
        self.waypoints_container.setModel(self.waypoints_listmodel)

        self.load_default_trajectory_2()
        self.backend.add_poll_callback(self.on_poll_response)
    
    def setupSignals(self):
        self._connected_signal.connect(self._connected)
        self._disconnected_signal.connect(self._disconnected)

        self._helper.cf.connected.add_callback(
            self._connected_signal.emit)
        self._helper.cf.disconnected.add_callback(
            self._disconnected_signal.emit)

        self.bt_start.clicked.connect(self.backend.on_start)
        self.bt_land.clicked.connect(self.backend.on_land)
        self.bt_emergency_stop.clicked.connect(self.backend.on_emergency_stop)
        self.bt_unlock.clicked.connect(self.backend.on_unlock)
        self.bt_system_reset.clicked.connect(self.backend.on_system_reset)
        self.bt_greetings.clicked.connect(self.backend.on_greetings)

        self.bt_add.clicked.connect(self.on_add_waypoint)
        self.bt_import.clicked.connect(self.on_import_waypoint)
        self.bt_override.clicked.connect(self.on_override_waypoint)
        self.bt_erase_all.clicked.connect(self.on_erase_all_waypoints)
        self.bt_remove.clicked.connect(self.on_remove_waypoint)

        self.bt_upload.clicked.connect(self.on_upload)
        self.bt_export_as_trajectory.clicked.connect(self.on_export_as_trajectory)
        # self.bt_send_to_waypoints.clicked.connect(self.on_send_to_waypoints)

        self.bt_hover1.clicked.connect(self.on_hover1)
        self.bt_hover2.clicked.connect(self.on_hover2)
        self.bt_follow1.clicked.connect(self.on_follow1)
        self.bt_follow2.clicked.connect(self.on_follow2)

        self.rbt_absolute_x.clicked.connect(lambda: self.lb_x.setText("X pos:"))
        self.rbt_absolute_x.clicked.connect(lambda: self.lb_units_x.setText("[m]"))
        self.rbt_velocity_x.clicked.connect(lambda: self.lb_x.setText("X vel:"))
        self.rbt_velocity_x.clicked.connect(lambda: self.lb_units_x.setText("[m/s]"))
        self.rbt_absolute_y.clicked.connect(lambda: self.lb_y.setText("Y pos:"))
        self.rbt_absolute_y.clicked.connect(lambda: self.lb_units_y.setText("[m]"))
        self.rbt_velocity_y.clicked.connect(lambda: self.lb_y.setText("Y vel:"))
        self.rbt_velocity_y.clicked.connect(lambda: self.lb_units_y.setText("[m/s]"))
        self.rbt_absolute_z.clicked.connect(lambda: self.lb_z.setText("Z pos:"))
        self.rbt_absolute_z.clicked.connect(lambda: self.lb_units_z.setText("[m]"))
        self.rbt_velocity_z.clicked.connect(lambda: self.lb_z.setText("Z vel:"))
        self.rbt_velocity_z.clicked.connect(lambda: self.lb_units_z.setText("[m/s]"))

        self.rbt_absolute_yaw.clicked.connect(lambda: self.lb_yaw.setText("Yaw angle:"))
        self.rbt_absolute_yaw.clicked.connect(lambda: self.lb_units_yaw.setText("[deg]"))
        self.rbt_velocity_yaw.clicked.connect(lambda: self.lb_yaw.setText("Yaw rate:"))
        self.rbt_velocity_yaw.clicked.connect(lambda: self.lb_units_yaw.setText("[deg/s]"))
        self.rbt_absolute_pitch.clicked.connect(lambda: self.lb_pitch.setText("Pitch angle:"))
        self.rbt_absolute_pitch.clicked.connect(lambda: self.lb_units_pitch.setText("[deg]"))
        self.rbt_velocity_pitch.clicked.connect(lambda: self.lb_pitch.setText("Pitch rate:"))
        self.rbt_velocity_pitch.clicked.connect(lambda: self.lb_units_pitch.setText("[deg/s]"))
        self.rbt_absolute_roll.clicked.connect(lambda: self.lb_roll.setText("Roll angle:"))
        self.rbt_absolute_roll.clicked.connect(lambda: self.lb_units_roll.setText("[deg]"))
        self.rbt_velocity_roll.clicked.connect(lambda: self.lb_roll.setText("Roll rate:"))
        self.rbt_velocity_roll.clicked.connect(lambda: self.lb_units_roll.setText("[deg/s]"))

        self.rbt_high_level.clicked.connect(self.on_rbt_high_level_clicked)
        self.rbt_low_level.clicked.connect(self.on_rbt_low_level_clicked)

        self.rbt_hl_param_velocity.clicked.connect(lambda: self.lb_param_units.setText("[cm/s]"))
        self.rbt_hl_param_time.clicked.connect(lambda: self.lb_param_units.setText("[s]"))

        self.rdbt_is_leader.clicked.connect(self.on_is_leader)
        self.rdbt_p2p_system.clicked.connect(self.on_p2p_system)
        self.spbx_p2p_address.setValue(self.backend.p2p_address)
        self.spbx_p2p_address.valueChanged.connect(lambda spbx_p2p_address=self.spbx_p2p_address: self.backend.set_p2p_address(self.spbx_p2p_address.value()))

        self.lned_name.setText("TO")
    
    def on_poll_response(self, poll_packet: Protocol.GS_PACKET_POLL_PACKET):
        # print("Poll response:")
        # print("State: {}".format(poll_packet.state))
        # print("Is leader {}".format(poll_packet.is_leader))
        # print("x: {}".format(poll_packet.x))
        # print("y: {}".format(poll_packet.y))
        # print("z: {}".format(poll_packet.z))
        # print("yaw: {}".format(poll_packet.yaw))
        # print("pitch: {}".format(poll_packet.pitch))
        # print("roll: {}".format(poll_packet.roll))
        self.rdbt_is_leader.setChecked(True if poll_packet.is_leader == 1 else False)
    
    def on_p2p_system(self):
        self.backend.set_p2p_system(self.rdbt_p2p_system.isChecked())
        self.backend.set_p2p_address(self.spbx_p2p_address.value())
    
    def on_is_leader(self):
        if not self.backend.is_connected:
            self.rdbt_is_leader.setChecked(False)
        else:
            if self.rdbt_is_leader.isChecked():
                self.rdbt_is_leader.setChecked(False)
                self.backend.on_take_leader()
            else:
                self.rdbt_is_leader.setChecked(True)
    
    # def get_p2p_address(self):
    #     return self.spbx_p2p_address.value()
    
    def on_rbt_high_level_clicked(self):
        if self.rbt_follow.isChecked():
            self.gpbx_high_level_parameters.setTitle("Command duration:")
            self.lb_param_units.setText("[s]")
        else:
            self.gpbx_high_level_parameters.setTitle("High level parameters:")
            if self.rbt_hl_param_velocity.isChecked():
                self.lb_param_units.setText("[cm/s]")
            else:
                self.lb_param_units.setText("[s]")
    
    def on_rbt_low_level_clicked(self):
        self.gpbx_high_level_parameters.setTitle("Command duration:")
        self.lb_param_units.setText("[s]")
    
    # def set_unique_radiobutton(self, radiobutton_group):
    #     for rb in radiobutton_group:
    #         rb.clicked.connect()
    def on_add_waypoint(self):
        if not self.is_waypoint_valid():
            return
        elif self.does_waypoint_already_exist():
            msgBox = QMessageBox()
            msgBox.setInformativeText("Waypoint name aready in use...")
            msgBox.exec()
            return
        self.add_waypoint(self.get_waypoint())
    def add_waypoint(self, waypoint):
        self.waypoints.append(waypoint)
        self.waypoint_items.append(QStandardItem(waypoint.name))
        self.waypoints_listmodel.appendRow(self.waypoint_items[-1])
    def on_override_waypoint(self):
        selected_indexes = self.waypoints_container.selectedIndexes()
        if len(selected_indexes) < 1:
            msgBox = QMessageBox()
            msgBox.setInformativeText("You need to select an existing waypoint to override...")
            msgBox.exec()
            return
        selected_index = selected_indexes[0].row()
        if not self.is_waypoint_valid():
            return
        elif self.does_waypoint_already_exist(ignore=selected_index):
            msgBox = QMessageBox()
            msgBox.setInformativeText("Waypoint name aready in use...")
            msgBox.exec()
            return
        self.waypoints.pop(selected_index)
        self.waypoint_items.pop(selected_index)
        self.waypoints_listmodel.removeRow(selected_index)

        waypoint = self.get_waypoint()
        waypoint_item = QStandardItem(waypoint.name)

        self.waypoints.insert(selected_index, waypoint)
        self.waypoint_items.insert(selected_index, waypoint_item)
        self.waypoints_listmodel.insertRow(selected_index, waypoint_item)

        waypoint_index = self.waypoints_listmodel.index(selected_index, 0)
        self.waypoints_container.setCurrentIndex(waypoint_index)
    def on_erase_all_waypoints(self):
        self.waypoints.clear()
        self.waypoint_items.clear()
        self.waypoints_listmodel.clear()
    def on_remove_waypoint(self):
        selected_indexes = self.waypoints_container.selectedIndexes()
        if len(selected_indexes) < 1:
            msgBox = QMessageBox()
            msgBox.setInformativeText("You need to select an existing waypoint to remove...")
            msgBox.exec()
            return
        selected_index: QModelIndex = selected_indexes[0].row()
        self.waypoints.pop(selected_index)
        self.waypoint_items.pop(selected_index)
        self.waypoints_listmodel.removeRow(selected_index)

    def on_upload(self):
        for waypoint in self.waypoints:
            self.backend.send_waypoint(waypoint)
    def on_export_as_trajectory(self):
        pass
    def on_send_to_waypoints(self):
        pass

    def _connected(self, link_uri):
        self.lb_connectivity_state.setText("State: Connected")
    def _disconnected(self, link_uri):
        self.lb_connectivity_state.setText("State: Disconnected")
    
    def does_waypoint_already_exist(self, ignore=None):
        if self.lned_name.text().upper() in [wp.name for wp, i in zip(self.waypoints, range(len(self.waypoints))) if i != ignore]:
            return True
        return False
    def is_waypoint_valid(self):
        wpname = self.lned_name.text().upper()
        if len(wpname) < 1:
            msgBox = QMessageBox()
            msgBox.setInformativeText("Waypoint name must not be empty...")
            msgBox.exec()
            return False
        elif len(wpname) > 5:
            msgBox = QMessageBox()
            msgBox.setInformativeText("Waypoint name must not exceed five letters...")
            msgBox.exec()
            return False
        else:
            if not re.match("^[A-Z0-9]{1,5}", wpname):
                msgBox = QMessageBox()
                msgBox.setInformativeText("Only capital letters and numbers are accepted...")
                msgBox.exec()
                return False
        return True
    
    def get_waypoint(self):
        waypoint = Waypoint()
        waypoint.name = self.lned_name.text().upper()
        waypoint.parameters.controller = \
            CONTROLLER_TYPE.CASCATED_PID if self.rbt_cascated_pid.isChecked() else \
            CONTROLLER_TYPE.MELLINGER if self.rbt_mellinger.isChecked() else \
            CONTROLLER_TYPE.INDI if self.rbt_indi.isChecked() else \
            CONTROLLER_TYPE.BRESCIANINI if self.rbt_brescianini.isChecked() else \
            CONTROLLER_TYPE.LEE if self.rbt_lee.isChecked() else \
            CONTROLLER_TYPE.LIS if self.rbt_lis.isChecked() else \
            CONTROLLER_TYPE.CASCATED_PID
        waypoint.parameters.modes_position.x = \
            WAYPOINT_MODE.DISABLED if self.rbt_disabled_x.isChecked() else \
            WAYPOINT_MODE.ABSOLUTE if self.rbt_absolute_x.isChecked() else \
            WAYPOINT_MODE.VELOCITY if self.rbt_velocity_x.isChecked() else \
            WAYPOINT_MODE.DISABLED
        waypoint.parameters.modes_position.y = \
            WAYPOINT_MODE.DISABLED if self.rbt_disabled_y.isChecked() else \
            WAYPOINT_MODE.ABSOLUTE if self.rbt_absolute_y.isChecked() else \
            WAYPOINT_MODE.VELOCITY if self.rbt_velocity_y.isChecked() else \
            WAYPOINT_MODE.DISABLED
        waypoint.parameters.modes_position.z = \
            WAYPOINT_MODE.DISABLED if self.rbt_disabled_z.isChecked() else \
            WAYPOINT_MODE.ABSOLUTE if self.rbt_absolute_z.isChecked() else \
            WAYPOINT_MODE.VELOCITY if self.rbt_velocity_z.isChecked() else \
            WAYPOINT_MODE.DISABLED
        waypoint.parameters.modes_attitude.yaw = \
            WAYPOINT_MODE.DISABLED if self.rbt_disabled_yaw.isChecked() else \
            WAYPOINT_MODE.ABSOLUTE if self.rbt_absolute_yaw.isChecked() else \
            WAYPOINT_MODE.VELOCITY if self.rbt_velocity_yaw.isChecked() else \
            WAYPOINT_MODE.DISABLED
        waypoint.parameters.modes_attitude.pitch = \
            WAYPOINT_MODE.DISABLED if self.rbt_disabled_pitch.isChecked() else \
            WAYPOINT_MODE.ABSOLUTE if self.rbt_absolute_pitch.isChecked() else \
            WAYPOINT_MODE.VELOCITY if self.rbt_velocity_pitch.isChecked() else \
            WAYPOINT_MODE.DISABLED
        waypoint.parameters.modes_attitude.roll = \
            WAYPOINT_MODE.DISABLED if self.rbt_disabled_roll.isChecked() else \
            WAYPOINT_MODE.ABSOLUTE if self.rbt_absolute_roll.isChecked() else \
            WAYPOINT_MODE.VELOCITY if self.rbt_velocity_roll.isChecked() else \
            WAYPOINT_MODE.DISABLED
        waypoint.parameters.command_type = \
            WAYPOINT_COMMAND_TYPE.DIRECT if self.rbt_low_level.isChecked() else \
            WAYPOINT_COMMAND_TYPE.HIGH_LEVEL if self.rbt_high_level.isChecked() else \
            WAYPOINT_COMMAND_TYPE.DIRECT
        waypoint.parameters.hl_command_type = \
            WAYPOINT_HL_COMMAND_TYPE.VELOCITY if self.rbt_hl_param_velocity.isChecked() else \
            WAYPOINT_HL_COMMAND_TYPE.TIME if self.rbt_hl_param_time.isChecked() else \
            WAYPOINT_HL_COMMAND_TYPE.VELOCITY
        waypoint.parameters.type = \
            WAYPOINT_TYPE.TAKE_OFF if self.rbt_takeoff.isChecked() else \
            WAYPOINT_TYPE.GOTO if self.rbt_goto.isChecked() else \
            WAYPOINT_TYPE.HOVER if self.rbt_hover.isChecked() else \
            WAYPOINT_TYPE.FOLLOW if self.rbt_follow.isChecked() else \
            WAYPOINT_TYPE.LAND if self.rbt_land.isChecked() else \
            WAYPOINT_TYPE.IDLE if self.rbt_idle.isChecked() else \
            WAYPOINT_TYPE.SHUTDOWN if self.rbt_shutdown.isChecked() else \
            WAYPOINT_TYPE.LOOP_BEGIN if self.rbt_loop_begin.isChecked() else \
            WAYPOINT_TYPE.LOOP_END if self.rbt_loop_end.isChecked() else \
            WAYPOINT_TYPE.OTHER if self.rbt_other.isChecked() else \
            WAYPOINT_TYPE.TAKE_OFF
        waypoint.position.x = int(self.sb_x.value()*1000.0)
        waypoint.position.y = int(self.sb_y.value()*1000.0)
        waypoint.position.z = int(self.sb_z.value()*1000.0)
        waypoint.attitude.yaw = int(self.sb_yaw.value()*1000.0/180.0*3.14159265)
        waypoint.attitude.pitch = int(self.sb_pitch.value()*1000.0/180.0*3.14159265)
        waypoint.attitude.roll = int(self.sb_roll.value()*1000.0/180.0*3.14159265)
        waypoint.loop_count = self.spbx_loop.value()
        waypoint.parameters.follow_position_reference = \
            WAYPOINT_FOLLOW_REFERENCE.GLOBAL if self.rbt_global.isChecked() else \
            WAYPOINT_FOLLOW_REFERENCE.RELATIVE if self.rbt_relative.isChecked() else \
            WAYPOINT_FOLLOW_REFERENCE.GLOBAL
        waypoint.parameters.follow_yaw_reference = \
            WAYPOINT_FOLLOW_REFERENCE.RELATIVE if self.chbx_attitude_relative.isChecked() else \
            WAYPOINT_FOLLOW_REFERENCE.GLOBAL
        if self.rbt_follow.isChecked() or self.rbt_low_level.isChecked():
            waypoint.type_parameter = self.spbx_follow_address.value()
            waypoint.hl_command_parameter = int(self.spbx_hl_command_parameter.value()*10.0)
        else:
            waypoint.type_parameter = self.spbx_type_parameter.value()
            if self.rbt_hl_param_time.isChecked():
                waypoint.hl_command_parameter = int(self.spbx_hl_command_parameter.value()*10.0)
            else:
                waypoint.hl_command_parameter = int(self.spbx_hl_command_parameter.value())
        return waypoint
    
    def on_import_waypoint(self):
        selected_indexes = self.waypoints_container.selectedIndexes()
        if len(selected_indexes) < 1:
            return
        selected_index: QModelIndex = selected_indexes[0]
        waypoint: Waypoint = self.waypoints[selected_index.row()]

        if waypoint.parameters.type == WAYPOINT_TYPE.TAKE_OFF:
            self.rbt_takeoff.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.GOTO:
            self.rbt_goto.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.HOVER:
            self.rbt_hover.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.FOLLOW:
            self.rbt_follow.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.LAND:
            self.rbt_land.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.IDLE:
            self.rbt_idle.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.SHUTDOWN:
            self.rbt_shutdown.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.LOOP_BEGIN:
            self.rbt_loop_begin.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.LOOP_END:
            self.rbt_loop_end.setChecked(True)
        elif waypoint.parameters.type == WAYPOINT_TYPE.OTHER:
            self.rbt_other.setChecked(True)
        
        if waypoint.parameters.controller == CONTROLLER_TYPE.CASCATED_PID:
            self.rbt_cascated_pid.setChecked(True)
        elif waypoint.parameters.controller == CONTROLLER_TYPE.MELLINGER:
            self.rbt_mellinger.setChecked(True)
        elif waypoint.parameters.controller == CONTROLLER_TYPE.INDI:
            self.rbt_indi.setChecked(True)
        elif waypoint.parameters.controller == CONTROLLER_TYPE.BRESCIANINI:
            self.rbt_brescianini.setChecked(True)
        elif waypoint.parameters.controller == CONTROLLER_TYPE.LEE:
            self.rbt_lee.setChecked(True)
        elif waypoint.parameters.controller == CONTROLLER_TYPE.LIS:
            self.rbt_lis.setChecked(True)
        
        if waypoint.parameters.modes_position.x == WAYPOINT_MODE.DISABLED:
            self.rbt_disabled_x.setChecked(True)
        elif waypoint.parameters.modes_position.x == WAYPOINT_MODE.ABSOLUTE:
            self.rbt_absolute_x.setChecked(True)
        elif waypoint.parameters.modes_position.x == WAYPOINT_MODE.VELOCITY:
            self.rbt_velocity_x.setChecked(True)
        if waypoint.parameters.modes_position.y == WAYPOINT_MODE.DISABLED:
            self.rbt_disabled_y.setChecked(True)
        elif waypoint.parameters.modes_position.y == WAYPOINT_MODE.ABSOLUTE:
            self.rbt_absolute_y.setChecked(True)
        elif waypoint.parameters.modes_position.y == WAYPOINT_MODE.VELOCITY:
            self.rbt_velocity_y.setChecked(True)
        if waypoint.parameters.modes_position.z == WAYPOINT_MODE.DISABLED:
            self.rbt_disabled_z.setChecked(True)
        elif waypoint.parameters.modes_position.z == WAYPOINT_MODE.ABSOLUTE:
            self.rbt_absolute_z.setChecked(True)
        elif waypoint.parameters.modes_position.z == WAYPOINT_MODE.VELOCITY:
            self.rbt_velocity_z.setChecked(True)
        
        if waypoint.parameters.modes_attitude.yaw == WAYPOINT_MODE.DISABLED:
            self.rbt_disabled_yaw.setChecked(True)
        elif waypoint.parameters.modes_attitude.yaw == WAYPOINT_MODE.ABSOLUTE:
            self.rbt_absolute_yaw.setChecked(True)
        elif waypoint.parameters.modes_attitude.yaw == WAYPOINT_MODE.VELOCITY:
            self.rbt_velocity_yaw.setChecked(True)
        if waypoint.parameters.modes_attitude.roll == WAYPOINT_MODE.DISABLED:
            self.rbt_disabled_roll.setChecked(True)
        elif waypoint.parameters.modes_attitude.roll == WAYPOINT_MODE.ABSOLUTE:
            self.rbt_absolute_roll.setChecked(True)
        elif waypoint.modes_attitude.roll == WAYPOINT_MODE.VELOCITY:
            self.rbt_velocity_roll.setChecked(True)
        if waypoint.parameters.modes_attitude.pitch == WAYPOINT_MODE.DISABLED:
            self.rbt_disabled_pitch.setChecked(True)
        elif waypoint.parameters.modes_attitude.pitch == WAYPOINT_MODE.ABSOLUTE:
            self.rbt_absolute_pitch.setChecked(True)
        elif waypoint.parameters.modes_attitude.pitch == WAYPOINT_MODE.VELOCITY:
            self.rbt_velocity_pitch.setChecked(True)
        
        if waypoint.parameters.command_type == WAYPOINT_COMMAND_TYPE.HIGH_LEVEL:
            self.rbt_high_level.setChecked(True)
        if waypoint.parameters.command_type == WAYPOINT_COMMAND_TYPE.DIRECT:
            self.rbt_low_level.setChecked(True)
        
        if waypoint.parameters.hl_command_type == WAYPOINT_HL_COMMAND_TYPE.VELOCITY:
            self.rbt_hl_param_velocity.setChecked(True)
        elif waypoint.parameters.hl_command_type == WAYPOINT_HL_COMMAND_TYPE.TIME:
            self.rbt_hl_param_time.setChecked(True)
        
        if waypoint.parameters.follow_position_reference == WAYPOINT_FOLLOW_REFERENCE.GLOBAL:
            self.rbt_global.setChecked(True)
        elif waypoint.parameters.follow_position_reference == WAYPOINT_FOLLOW_REFERENCE.RELATIVE:
            self.rbt_relative.setChecked(True)
        
        self.lned_name.setText(waypoint.name)
        self.sb_x.setValue(waypoint.position.x/1000.0)
        self.sb_y.setValue(waypoint.position.y/1000.0)
        self.sb_z.setValue(waypoint.position.z/1000.0)
        self.sb_yaw.setValue(waypoint.attitude.yaw/1000.0/3.14159265*180.0)
        self.sb_pitch.setValue(waypoint.attitude.pitch/1000.0/3.14159265*180.0)
        self.sb_roll.setValue(waypoint.attitude.roll/1000.0/3.14159265*180.0)
        self.spbx_follow_address.setValue(struct.unpack("<BB", struct.pack("<h", waypoint.type_parameter))[0])
        if waypoint.parameters.type == WAYPOINT_TYPE.FOLLOW or waypoint.parameters.command_type == WAYPOINT_COMMAND_TYPE.DIRECT:
            self.spbx_hl_command_parameter.setValue(waypoint.hl_command_parameter/10)
            self.lb_param_units.setText("[s]")
            self.lb_param_high_level.setText("")
            self.gpbx_high_level_parameters.setTitle("Command duration:");
        else:
            self.gpbx_high_level_parameters.setTitle("High level parameters:");
            if waypoint.parameters.hl_command_type == WAYPOINT_HL_COMMAND_TYPE.TIME:
                self.spbx_hl_command_parameter.setValue(waypoint.hl_command_parameter/10)
                self.lb_param_units.setText("[s]")
            else:
                self.spbx_hl_command_parameter.setValue(waypoint.hl_command_parameter)
                self.lb_param_units.setText("[cm/s]")
        self.spbx_loop.setValue(waypoint.loop_count)
        self.chbx_attitude_relative.setChecked(
            False if waypoint.parameters.follow_yaw_reference == WAYPOINT_FOLLOW_REFERENCE.GLOBAL else \
            True if waypoint.parameters.follow_yaw_reference == WAYPOINT_FOLLOW_REFERENCE.RELATIVE else \
            False)
    
    def load_default_trajectory_1(self):
        to_wp = Waypoint()
        to_wp.name = "TO"
        to_wp.parameters.type = WAYPOINT_TYPE.TAKE_OFF
        to_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        to_wp.hl_command_parameter = 10
        to_wp.position.x = 1000
        to_wp.position.y = 1000
        to_wp.position.z = 1000

        lb_wp = Waypoint()
        lb_wp.name = "LB"
        lb_wp.parameters.type = WAYPOINT_TYPE.LOOP_BEGIN

        h1_wp = Waypoint()
        h1_wp.name = "H1"
        h1_wp.parameters.type = WAYPOINT_TYPE.HOVER
        h1_wp.parameters.controller = CONTROLLER_TYPE.LEE
        h1_wp.parameters.modes_position.x = WAYPOINT_MODE.ABSOLUTE
        h1_wp.parameters.modes_position.y = WAYPOINT_MODE.ABSOLUTE
        h1_wp.parameters.modes_position.z = WAYPOINT_MODE.ABSOLUTE
        h1_wp.position.x = 750
        h1_wp.position.y = 750
        h1_wp.position.z = 1500
        h1_wp.attitude.yaw = int(0*1000/180.0*3.14159265)
        h1_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        h1_wp.hl_command_parameter = 20
        
        h2_wp = h1_wp.copy()
        h2_wp.name = "H2"
        h2_wp.attitude.yaw = int(90*1000/180.0*3.14159265)
        h3_wp = h1_wp.copy()
        h3_wp.name = "H3"
        h3_wp.attitude.yaw = int(180*1000/180.0*3.14159265)
        h4_wp = h1_wp.copy()
        h4_wp.name = "H4"
        h4_wp.attitude.yaw = int(270*1000/180.0*3.14159265)

        le_wp = Waypoint()
        le_wp.name = "LE"
        le_wp.parameters.type = WAYPOINT_TYPE.LOOP_END
        le_wp.loop_count = 10

        ld_wp = Waypoint()
        ld_wp.name = "L"
        ld_wp.parameters.type = WAYPOINT_TYPE.LAND
        ld_wp.position.x = 1000
        ld_wp.position.y = 1000

        waypoints = [to_wp, lb_wp, h1_wp, h2_wp, h3_wp, h4_wp, le_wp, ld_wp]
        self.on_erase_all_waypoints()
        for wp in waypoints:
            self.add_waypoint(wp)
    
    def load_default_trajectory_2(self):
        to_wp = Waypoint()
        to_wp.name = "TO"
        to_wp.parameters.type = WAYPOINT_TYPE.TAKE_OFF
        to_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        to_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        to_wp.hl_command_parameter = 10
        to_wp.position.x = 1000
        to_wp.position.y = 1000
        to_wp.position.z = 1000
        to_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        lb_wp = Waypoint()
        lb_wp.name = "LB"
        lb_wp.parameters.type = WAYPOINT_TYPE.LOOP_BEGIN

        h1_wp = Waypoint()
        h1_wp.name = "H1"
        h1_wp.parameters.type = WAYPOINT_TYPE.HOVER
        h1_wp.parameters.controller = CONTROLLER_TYPE.LEE
        h1_wp.parameters.modes_position.x = WAYPOINT_MODE.ABSOLUTE
        h1_wp.parameters.modes_position.y = WAYPOINT_MODE.ABSOLUTE
        h1_wp.parameters.modes_position.z = WAYPOINT_MODE.ABSOLUTE
        h1_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        h1_wp.position.x = 1000
        h1_wp.position.y = 100
        h1_wp.position.z = 1500
        h1_wp.attitude.yaw = int(90*1000/180.0*3.14159265)
        h1_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        h1_wp.hl_command_parameter = 40
        h1_wp.parameters.command_type = WAYPOINT_COMMAND_TYPE.HIGH_LEVEL
        
        h2_wp = h1_wp.copy()
        h2_wp.name = "H2"
        h2_wp.position.x = 1900
        h2_wp.position.y = 1000
        h2_wp.attitude.yaw = int(180*1000/180.0*3.14159265)
        
        h3_wp = h2_wp.copy()
        h3_wp.name = "H3"
        h3_wp.position.x = 1000
        h3_wp.position.y = 1900
        h3_wp.attitude.yaw = int(270*1000/180.0*3.14159265)
        
        h4_wp = h3_wp.copy()
        h4_wp.name = "H4"
        h4_wp.position.x = 100
        h4_wp.position.y = 1000
        h4_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        le_wp = Waypoint()
        le_wp.name = "LE"
        le_wp.parameters.type = WAYPOINT_TYPE.LOOP_END
        le_wp.loop_count = 2

        ld_wp = Waypoint()
        ld_wp.name = "L"
        ld_wp.parameters.type = WAYPOINT_TYPE.LAND
        ld_wp.parameters.controller = CONTROLLER_TYPE.LEE
        ld_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        ld_wp.position.x = 1000
        ld_wp.position.y = 1000
        ld_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        waypoints = [to_wp, lb_wp, h1_wp, h2_wp, h3_wp, h4_wp, le_wp, ld_wp]
        self.on_erase_all_waypoints()
        for wp in waypoints:
            self.add_waypoint(wp)
    
    def on_hover1(self):
        self.load_default_trajectory_1()
    def on_hover2(self):
        self.load_default_trajectory_2()

    def on_follow1(self):
        to_wp = Waypoint()
        to_wp.name = "TO"
        to_wp.parameters.type = WAYPOINT_TYPE.TAKE_OFF
        to_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        to_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        to_wp.hl_command_parameter = 10
        to_wp.position.x = 1500
        to_wp.position.y = 1500
        to_wp.position.z = 1000
        to_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        f_wp = Waypoint()
        f_wp.name = "F"
        f_wp.parameters.type = WAYPOINT_TYPE.FOLLOW
        f_wp.parameters.controller = CONTROLLER_TYPE.LEE
        f_wp.parameters.modes_position.x = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.modes_position.y = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.modes_position.z = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.follow_position_reference = WAYPOINT_FOLLOW_REFERENCE.RELATIVE
        f_wp.parameters.follow_attitude_reference = WAYPOINT_FOLLOW_REFERENCE.RELATIVE
        f_wp.position.x = 750
        f_wp.position.y = 0
        f_wp.position.z = 0
        f_wp.attitude.yaw = int(90*1000/180.0*3.14159265)
        f_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        f_wp.type_parameter = 0xE4
        f_wp.hl_command_parameter = int(20.0*10)
        f_wp.parameters.command_type = WAYPOINT_COMMAND_TYPE.DIRECT

        ld_wp = Waypoint()
        ld_wp.name = "L"
        ld_wp.parameters.type = WAYPOINT_TYPE.LAND
        ld_wp.parameters.controller = CONTROLLER_TYPE.LEE
        ld_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        ld_wp.position.x = 1500
        ld_wp.position.y = 1500
        ld_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        waypoints = [to_wp, f_wp, ld_wp]
        self.on_erase_all_waypoints()
        for wp in waypoints:
            self.add_waypoint(wp)
        
    def on_follow2(self):
        to_wp = Waypoint()
        to_wp.name = "TO"
        to_wp.parameters.type = WAYPOINT_TYPE.TAKE_OFF
        to_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        to_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        to_wp.hl_command_parameter = 10
        to_wp.position.x = 1500
        to_wp.position.y = 1500
        to_wp.position.z = 1000
        to_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        f_wp = Waypoint()
        f_wp.name = "F"
        f_wp.parameters.type = WAYPOINT_TYPE.FOLLOW
        f_wp.parameters.controller = CONTROLLER_TYPE.LEE
        f_wp.parameters.modes_position.x = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.modes_position.y = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.modes_position.z = WAYPOINT_MODE.ABSOLUTE
        f_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        f_wp.position.x = 0
        f_wp.position.y = 300
        f_wp.position.z = 0
        f_wp.attitude.yaw = int(180*1000/180.0*3.14159265)
        f_wp.parameters.hl_command_type = WAYPOINT_HL_COMMAND_TYPE.TIME
        f_wp.type_parameter = 0xE4
        f_wp.hl_command_parameter = int(20.0*10)
        f_wp.parameters.command_type = WAYPOINT_COMMAND_TYPE.DIRECT

        ld_wp = Waypoint()
        ld_wp.name = "L"
        ld_wp.parameters.type = WAYPOINT_TYPE.LAND
        ld_wp.parameters.controller = CONTROLLER_TYPE.LEE
        ld_wp.parameters.modes_attitude.yaw = WAYPOINT_MODE.ABSOLUTE
        ld_wp.position.x = 1500
        ld_wp.position.y = 1500
        ld_wp.attitude.yaw = int(0*1000/180.0*3.14159265)

        waypoints = [to_wp, f_wp, ld_wp]
        self.on_erase_all_waypoints()
        for wp in waypoints:
            self.add_waypoint(wp)