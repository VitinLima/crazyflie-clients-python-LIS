import logging

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtGui import QColor

import lis
from lis.__init__ import lis_backend
import lis.ui
import lis.ui.tabs
import lis.ui.tabs.PyQtGraphCanvas
import lis.Backend
from lis.Backend import default_log_configs

__author__ = 'Stagiaires au Laboratoir d\'Ingénierie de Systèmes de l\'École Nationale Supérieure d\'Ingénieurs de Caen'
__all__ = ['LISPlotTab']

logger = logging.getLogger(__name__)

log_options_class = uic.loadUiType(lis.module_path + "/ui/dialogs/log_options_dialog.ui")[0]

default_colors_options = [
    "red",
    "Orange",
    "Yellow",
    "Yellowish-Green",
    "Green",
    "Greenish-Cyan",
    "Cyan",
    "Blueish-Cyan",
    "Blue",
    "Purple",
    "Magenta",
    "Pink",
]

class LogOptionsDialog(QtWidgets.QDialog, log_options_class):
    def __init__(self, options):
        super(QtWidgets.QDialog, self).__init__()
        self.setupUi(self)
        self.setupSignals()

        self.lned_log_label.setText(options['label'])
        # self.cbbx_logging_variable
        self.spbx_pen_width.setValue(options['pen_width'])
        # if options['pen_color'] in default_colors_options:
        #     self.cbbx_pen_color.setCurrentIndex(options['pen_color'])
        #     pen_color = QColor(self.cbbx_pen_color).getRgb()
        #     self.lned_pen_color.setText("[{},{},{}]".format(pen_color[0],pen_color[1],pen_color[2]))
        #     print(pen_color)
        # else:
        #     self.cbbx_pen_color.setCurrentText("Custom")
        #     pen_color = options['pen_color'].getRgb()
        #     self.lned_pen_color.setText("[{},{},{}]".format(pen_color[0],pen_color[1],pen_color[2]))
        # self.lned_brush_color.setText(options['brush_color'])
        self.spbx_brush_transparency.setValue(options['brush_transparency'])
        if options['h_axis_side'] == 'top':
            self.rdbt_horizontal_axis_ontop.setChecked(True)
        else:
            self.rdbt_horizontal_axis_onbottom.setChecked(True)
        if options['v_axis_side'] == 'left':
            self.rdbt_vertical_axis_onleft.setChecked(True)
        else:
            self.rdbt_vertical_axis_onright.setChecked(True)
        for log_config in default_log_configs.values():
            for variable in log_config['variables']:
                self.cbbx_logging_variable.addItem(variable)
    
    def on_custom_color(self):
        self.cbbx_pen_color.setCurrentText("Custom")

    def setupSignals(self):
        pass
    
    def get_options(self):
        if self.cbbx_pen_color.currentText() == "Custom":
            pen_color = QColor(self.lned_pen_color.text())
        else:
            pen_color = QColor(self.cbbx_pen_color.currentText())
        options = dict(
            label = self.lned_log_label.text(),
            variable = self.cbbx_logging_variable.currentIndex(),
            pen_width = self.lned_pen_width.value(),
            # pen_color = pen_color,
            # brush_color = self.lned_brush_color.text(),
            brush_transparency = self.lned_brush_transparency.value(),
            h_axis_side = 'top' if self.rdbt_horizontal_axis_ontop.isChecked() else 'bottom',
            v_axis_side = 'right' if self.rdbt_vertical_axis_onright.isChecked() else 'left',
            h_axis_lim = 'auto' if self.chbx_horizontal_axis_autolim.isChecked() else [
                self.chbx_horizontal_axis_minlim.value(),
                self.chbx_horizontal_axis_maxlim.value()
              ],
            v_axis_lim = 'auto' if self.chbx_vertical_axis_autolim.isChecked() else [
                self.chbx_vertical_axis_minlim.value(),
                self.chbx_vertical_axis_maxlim.value()
              ]
            )
        return options

