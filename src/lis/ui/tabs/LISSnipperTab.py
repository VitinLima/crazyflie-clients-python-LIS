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
import numpy as np

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QMessageBox, QHBoxLayout, QTextEdit
from PyQt6.QtCore import QTimer

import lis
import cflib
import cflib.crazyflie
from cfclient.ui.tab_toolbox import TabToolbox

# cflib.crtp.init_drivers()

__author__ = 'Bitcraze AB'
__all__ = ['LISSnipperTab']

logger = logging.getLogger(__name__)

snipper_tab_class = uic.loadUiType(lis.module_path + "/ui/tabs/lisSnipperTab.ui")[0]


class AddressLogTab(QFrame):
    def __init__(self, address:int, **kwargs):
        super().__init__(**kwargs)
        self.address=address
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.textbox = QTextEdit(parent=self)
        self.layout.addWidget(self.textbox)
        self.textbox.setReadOnly(True)

class LISSnipperTab(TabToolbox, snipper_tab_class):
    """Tab for plotting logging data"""

    _connected_signal = pyqtSignal(str)
    _disconnected_signal = pyqtSignal(str)
    _connection_failed_signal = pyqtSignal(str, str)
    _received_char_signal = pyqtSignal(object)

    address_book = np.array([
        # 0xE0,
        0xE2,
        0xE4,
        # 0xE7,
        ])
    
    tabs = []

    def __init__(self, helper):
        super(LISSnipperTab, self).__init__(helper, 'LIS Snipper')
        self.setupUi(self)
        self.cf = helper.cf
        self.is_connected = False

        # Always wrap callbacks from Crazyflie API though QT Signal/Slots
        # to avoid manipulating the UI when rendering it
        self._connected_signal.connect(self._connected)
        self._disconnected_signal.connect(self._disconnected)
        self._connection_failed_signal.connect(self._connection_failed)
        self._received_char_signal.connect(self._received_char_)

        self.cf.connected.add_callback(self._connected_signal.emit)
        self.cf.disconnected.add_callback(self._disconnected_signal.emit)
        self.cf.connection_failed.add_callback(self._connection_failed_signal.emit)
        self.cf.console.receivedChar.add_callback(self._received_char_signal.emit)

        for address in self.address_book:
            self.tabs.append(AddressLogTab(address=address))
            self.tbwd_addresses.addTab(self.tabs[-1], hex(address))

        self.timer = QTimer(parent=self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.disconnect_timer = QTimer(parent=self)
        self.disconnect_timer.setInterval(50)
        self.disconnect_timer.timeout.connect(self.on_disconnect_timer_timeout)
        self.disconnect_timer.setSingleShot(True)

        self.bt_enable.clicked.connect(self.on_enable)
    
    def on_enable(self):
        if self.bt_enable.text() == "Enable":
            self.bt_enable.setText("Disable")
            self.timer.start()
        else:
            self.bt_enable.setText("Enable")
            self.timer.stop()
    
    def on_timer_timeout(self):
        if not self.is_connected:
            new_add = hex(self.address_book[0])[2:].upper()
            self.cf.open_link("radio://0/80/2M/E7E7E7E7{}".format(new_add))
            self.address_book = np.roll(self.address_book, 1)
            self.tabs = [self.tabs[-1]]+self.tabs[:-1]
    
    def on_disconnect_timer_timeout(self):
        if self.is_connected:
            self.cf.close_link()
    
    # def on_connect(self):
    #     self.cf.open_link("radio://0/80/2M/E7E7E7E7E2")

    def _connected(self, link_uri):
        """Callback when the Crazyflie has been connected"""
        self.is_connected = True
        print("Crazyflie connected to {}".format(link_uri))
        # self.cf.close_link()
        # self.disconnect_timer.start()
        # logger.debug

    def _disconnected(self, link_uri):
        """Callback for when the Crazyflie has been disconnected"""
        self.is_connected = False
        print("Crazyflie disconnected from {}".format(link_uri))

    def _connection_failed(self, link_uri, errmsg):
        """Callback when the Crazyflie has failed to connect"""
        print("Crazyflie failed to connected to {}: {}".format(link_uri, errmsg))

    def _received_char_(self, data):
        """Callback when the log layer receives new data"""
        self.tabs[-1].textbox.append(data)