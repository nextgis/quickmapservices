# -*- coding: utf-8 -*-

"""
***************************************************************************
    FileSelectionPanel.py
    ---------------------
    Date                 : August 2012
    Copyright            : (C) 2012 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
from __future__ import absolute_import
from .plugin_settings import PluginSettings

__author__ = 'Victor Olaya'
__date__ = 'August 2012'
__copyright__ = '(C) 2012, Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtWidgets import QFileDialog, QWidget, QHBoxLayout, QLineEdit, QToolButton
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt import QtCore
from .compat2qgis import getOpenFileName

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


class FileSelectionWidget(QWidget):

    def __init__(self, parent = None):
        super(FileSelectionWidget, self).__init__(None)
        self.setupUi(self)

        self.ext = '*'
        self.dialog_title = self.tr('Select folder')
        self.is_folder = False

        self.btnSelect.clicked.connect(self.show_selection_dialog)


    def show_selection_dialog(self):
        # Find the file dialog's working directory
        settings = QSettings()
        text = self.leText.text()
        if os.path.isdir(text):
            path = text
        elif os.path.isdir(os.path.dirname(text)):
            path = os.path.dirname(text)
        else:
            path = PluginSettings.last_icon_path()

        if self.is_folder:
            folder = QFileDialog.getExistingDirectory(self, self.dialog_title, path)
            if folder:
                self.leText.setText(folder)
                PluginSettings.set_last_icon_path(os.path.dirname(folder))
        else:
            filename = getOpenFileName(self, self.dialog_title, path, self.ext)
            if filename:
                self.leText.setText(filename)
                PluginSettings.set_last_icon_path(os.path.dirname(filename))

    def get_path(self):
        s = self.leText.text()
        if os.name == 'nt':
            s = s.replace('\\', '/')
        return s

    def set_path(self, text):
        self.leText.setText(text)

    def set_dialog_ext(self, ext):
        self.ext = ext

    def set_dialog_title(self, title):
        self.dialog_titledialog_title = title

    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(249, 23)
        self.horizontalLayout = QHBoxLayout(Form)
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.leText = QLineEdit(Form)
        self.leText.setReadOnly(True)
        self.leText.setObjectName(_fromUtf8("leText"))
        self.horizontalLayout.addWidget(self.leText)
        self.btnSelect = QToolButton(Form)
        self.btnSelect.setObjectName(_fromUtf8("btnSelect"))
        self.horizontalLayout.addWidget(self.btnSelect)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        #Form.setWindowTitle(self.tr(self.dialog_title))
        self.btnSelect.setText(self.tr("..."))
