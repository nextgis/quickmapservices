# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TileLayer Plugin
                                 A QGIS plugin
 Plugin layer for Tile Maps
                             -------------------
        begin                : 2012-12-16
        copyright            : (C) 2013 by Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtGui import QDialog, QDialogButtonBox, QPainter


CURR_PATH = os.path.dirname(__file__)
FORM_CLASS, _ = uic.loadUiType(os.path.join(CURR_PATH, 'propertiesdialog_base.ui'))


class PropertiesDialog(QDialog):
    applyClicked = pyqtSignal()

    def __init__(self, layer):
        QDialog.__init__(self)
        # set up the user interface
        self.ui = FORM_CLASS()
        self.ui.setupUi(self)
        self.setWindowTitle(u"%s - %s" % (self.tr("Layer Properties"), layer.name()))

        self.layer = layer
        # signals
        self.ui.horizontalSlider_Transparency.valueChanged.connect(self.ui.spinBox_Transparency.setValue)
        self.ui.spinBox_Transparency.valueChanged.connect(self.ui.horizontalSlider_Transparency.setValue)
        self.ui.horizontalSlider_Brightness.valueChanged.connect(self.ui.spinBox_Brightness.setValue)
        self.ui.spinBox_Brightness.valueChanged.connect(self.ui.horizontalSlider_Brightness.setValue)
        self.ui.horizontalSlider_Contrast.valueChanged.connect(lambda x: self.ui.doubleSpinBox_Contrast.setValue(x/100.0))
        self.ui.doubleSpinBox_Contrast.valueChanged.connect(lambda x: self.ui.horizontalSlider_Contrast.setValue(x*100))

        self.ui.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.applyClicked.emit)

        # set init values
        self.initBlendingCombo()
        self.ui.textEdit_Properties.setText(layer.metadata())
        self.ui.spinBox_Transparency.setValue(layer.transparency)
        self.ui.spinBox_Brightness.setValue(layer.brigthness)
        self.ui.doubleSpinBox_Contrast.setValue(layer.contrast)
        i = self.ui.comboBox_BlendingMode.findText(layer.blendModeName)
        if i != -1:
            self.ui.comboBox_BlendingMode.setCurrentIndex(i)

        self.ui.checkBox_SmoothRender.setChecked(layer.smoothRender)
        self.ui.checkBox_CreditVisibility.setChecked(layer.creditVisibility)
        self.ui.checkBox_Grayscale.setChecked(layer.grayscaleRender)

    def initBlendingCombo(self):
        attrs = dir(QPainter)
        for attr in attrs:
            if attr.startswith("CompositionMode_"):
                self.ui.comboBox_BlendingMode.addItem(attr[16:])


