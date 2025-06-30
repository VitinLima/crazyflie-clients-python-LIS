
import logging
import threading
from datetime import datetime
import time
import csv
import sys
import os
import random

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QFrame, QWidget, QScrollArea
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout
from PyQt6.QtWidgets import QPushButton, QCheckBox
from PyQt6.QtWidgets import QSizePolicy, QAbstractScrollArea
from PyQt6.QtCore import QTimer, Qt, QSize

import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import PyQt6.Qt6 as Qt6
import PyQt6.QtGui as QtGui
import PyQt6.QtQuick as QtQuick

import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
from PyQt6.QtGui import QPen, QBrush, QColor

from lis.__init__ import lis_backend
from lis.ui.dialogs.LogOptionsDialog import LogOptionsDialog
from lis.ui.dialogs.LogOptionsDialog import default_colors_options

import numpy as np


defaultSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)
defaultSizePolicy.setHorizontalStretch(0)
defaultSizePolicy.setVerticalStretch(0)
minimumSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
minimumSizePolicy.setHorizontalStretch(0)
minimumSizePolicy.setVerticalStretch(0)
defaultSizeConstraint = QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint

class LineOptions:
    pen=QPen()
    brush=QBrush()
    def copy(self):
        newOptions = LineOptions()
        newOptions.pen = self.pen
        newOptions.brush = self.brush
        return newOptions
class AxesOptions:
    title="Axes title"
    xlabel="X label"
    ylabel="Y label"
    zlabel="Z label"

class CanvasLog(QFrame):
    bt_config_signal = QtCore.pyqtSignal()

    def __init__(self, loggroup, logvariable, tab, label=None, canvas_id=0, line_options=LineOptions(), scale=1.0, **kwargs):
        super().__init__(**kwargs)
        self.loggroup=loggroup
        self.logvariable=logvariable
        self.tab=tab
        self.line_options=line_options
        self.canvas_id=canvas_id
        self.scale=scale
        if label is None:
            self.label=self.logvariable
        else:
            self.label=label
        self.layout: QHBoxLayout

        self.backend = lis_backend
        self.horizontal_axis = 'bottom'
        self.vertical_axis = 'left'

        self.init_layout()

        self.data = []
        self.timestamps = []
        self.line = None

        self.backend.add_callback_to_log(loggroup, self.callback)
        self.tab.canvas[self.canvas_id].add_listener(self)

        self.bt_config.clicked.connect(slot=self.on_config)
    
    def init_layout(self):
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.chbx = QCheckBox(parent=self, text=self.label)
        self.layout.addWidget(self.chbx)
        self.chbx.setChecked(True)

        self.bt_config = QPushButton(parent=self, text="Config...")
        self.layout.addWidget(self.bt_config)
    
    def on_config(self):
        dlg = LogOptionsDialog(self.get_options())
        if dlg.exec():
            self.set_options(dlg.get_options())

    def get_options(self):
        options = dict(
            label=self.label,
            pen_width=self.line_options.pen.width(),
            pen_color=self.line_options.pen.color(),
            brush_color=self.line_options.brush.color(),
            brush_transparency=self.line_options.brush.color().alpha()/255.0,
            h_axis_side=self.horizontal_axis,
            v_axis_side=self.vertical_axis
        )
        return options
    def set_options(self, options):
        self.label=options['label']
        # if options['pen_color'] in default_colors_options:
        #     self.line_options.pen=QPen(QColor(options['pen_color']), width=options['pen_width'])
        # else:
        #     pen_color = options['pen_color'].split(",[]")
        #     print(pen_color)
        # brush_color = QColor(options['brush_color'])
        # brush_color.setAlpha(int(255*options['brush_transparency']))
        # self.line_options.brush=QBrush(brush_color)
        self.horizontal_axis=options['h_axis_side']
        self.vertical_axis=options['v_axis_side']

    def callback(self, timestamp, data, logconf):
        self.data.append(data[self.logvariable])
        self.timestamps.append(timestamp)
    
    def get_data(self):
        if self.chbx.isChecked():
            timestamps = np.array(self.timestamps)/1000
            data = np.array(self.data)
            if self.tab.index_mode=="all":
                return np.array(self.timestamps), np.array(self.data)
            elif self.tab.index_mode=="indexes":
                index_threshold = self.tab.index_threshold
            elif self.tab.index_mode=="time":
                time_threshold = self.tab.time_threshold
                index_threshold = np.where(timestamps>timestamps[-1]-time_threshold)
                index_threshold = index_threshold[0]
            return timestamps[-index_threshold:-1], self.scale*data[-index_threshold:-1]
        else:
            return np.array([]), np.array([])
    
    def clear_draw(self, line_index, N_of_lines):
        if self.line is not None:
            self.line.clear()
            self.line = None
        self.fast_draw(line_index, N_of_lines)
    
    def fast_draw(self, line_index, N_of_lines):
        timestamps, data = self.get_data()
        if self.line is None:
            self.line = self.tab.canvas[self.canvas_id].plot(timestamps, data, pen=(line_index, N_of_lines), name=self.label)
        else:
            self.line.setData(timestamps, data)

class PlotCanvas(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.listeners = []
        self.options = AxesOptions()
        self.default_line_options = LineOptions()

        self.getPlotItem().setTitle(self.options.title)
        self.getPlotItem().setLabel('bottom', self.options.xlabel)
        self.getPlotItem().setLabel('left', self.options.ylabel)
        self.getPlotItem().addLegend()
    
    def setTitle(self, title):
        self.options.title = title
        self.getPlotItem().setTitle(title)
    def setXLabel(self, xlabel):
        self.options.xlabel = xlabel
        self.getPlotItem().setLabel('bottom', xlabel)
    def setYLabel(self, ylabel):
        self.options.ylabel = ylabel
        self.getPlotItem().setLabel('left', ylabel)
    
    def fast_draw(self):
        for listener,i in zip(self.listeners, range(len(self.listeners))):
            listener.fast_draw(line_index=i, N_of_lines=len(self.listeners))
    def clear_draw(self):
        self.getPlotItem().legend.clear()
        for listener,i in zip(self.listeners, range(len(self.listeners))):
            listener.clear_draw(line_index=i, N_of_lines=len(self.listeners))

    def add_listener(self, new_listener):
        self.listeners += [new_listener]
        self.clear_draw()
    def remove_listener(self, listener):
        self.listeners.remove(listener)
        self.clear_draw()

class PlotTab(QWidget):
    def __init__(self, fps_label=None, **kwargs):
        super().__init__(**kwargs)
        self.fps_label=fps_label

        self.logs = []
        self.canvas = []
        self.fps_target = 5
        self.last_redraw = time.time()
        self.fps_counter = np.zeros((5,))
        self.time_threshold = 3
        self.index_threshold = 100
        self.index_mode = "indexes"
        self.timer = QTimer(parent=self, timeout=self.notify_update)
        self.layout: QHBoxLayout

        self.init_layout()

        self.new_log_button.clicked.connect(self.on_new_log)
        self.config_button.clicked.connect(self.on_config)

        self.timer.start(int(1000/self.fps_target))

    def init_layout(self):
        scroll_area = QScrollArea(parent=self)
        scroll_area.setSizePolicy(minimumSizePolicy)
        self.new_log_button = QPushButton(parent=scroll_area, text="Add new...")
        self.config_button = QPushButton(parent=scroll_area, text="Config...")
        self.logs_list_layout = QVBoxLayout(scroll_area)
        self.logs_list_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        widget = QWidget(parent=scroll_area)
        widget.setSizePolicy(minimumSizePolicy)
        widget.setLayout(self.logs_list_layout)
        layout = QVBoxLayout(widget)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        layout.addWidget(widget)
        layout.addStretch()
        layout.addWidget(self.new_log_button)
        layout.addWidget(self.config_button)
        scroll_area.setLayout(layout)

        self.canvas_frame2 = QFrame(parent=self) # The Shennanigans I had to do to get the graph to auto-resize with the tab...
        self.canvas_frame2.setSizePolicy(defaultSizePolicy)
        self.canvas_frame2.setFrameShape(QFrame.Shape.Box)
        self.canvas_frame = QFrame(parent=self.canvas_frame2)
        self.canvas_frame.setSizePolicy(defaultSizePolicy)
        self.canvas_frame.setFrameShape(QFrame.Shape.Box)
        self.canvas_layout = QVBoxLayout(self.canvas_frame)
        self.canvas_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.canvas_frame.setLayout(self.canvas_layout)

        self.layout = QHBoxLayout(self)
        self.layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.layout.addWidget(scroll_area)
        self.layout.addWidget(self.canvas_frame2)
        self.setSizePolicy(defaultSizePolicy)
        self.setLayout(self.layout)

    def resizeEvent(self, ev: QtGui.QResizeEvent):
        super().resizeEvent(ev)
        self.canvas_frame.setFixedSize(self.canvas_frame2.size())
    
    def add_new_canvas(self):
        canvas = PlotCanvas(parent=self.canvas_frame)
        self.canvas.append(canvas)
        self.canvas_layout.addWidget(canvas)
        minH = self.canvas_frame2.minimumHeight()
        minH += 300
        self.canvas_frame2.setMinimumHeight(minH)
        return canvas
    
    def add_new_log(self, loggroup, logvariable, canvas_id, label, scale=1.0):
        canvasLog = CanvasLog(loggroup=loggroup, logvariable=logvariable, label=label, tab=self, canvas_id=canvas_id, scale=scale)
        self.logs += [canvasLog]
        self.logs_list_layout.addWidget(canvasLog)
    
    def on_new_log(self):
        pass
    
    def on_config(self):
        pass
    
    def notify_update(self):
        curtime = time.time()
        self.last_redraw = curtime
        for canvas in self.canvas:
            canvas.fast_draw()
        self.fps_counter = np.roll(self.fps_counter, (1,))
        self.fps_counter[0] = curtime
        if self.fps_label is not None:
            measured_fps = (len(self.fps_counter)-1)/(self.fps_counter[0]-self.fps_counter[-1])
            self.fps_label.setText("fps: {:.2f}".format(measured_fps))