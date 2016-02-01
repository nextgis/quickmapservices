# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QuickMapServices
                                 A QGIS plugin
 Collection of internet map services
                             -------------------
        begin                : 2014-11-21
        git sha              : $Format:%H$
        copyright            : (C) 2014 by NextGIS
        email                : info@nextgis.com
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

from PyQt4 import QtGui, uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMessageBox, QCursor
import sys
from qgis.core import QgsApplication
from extra_sources import ExtraSources
from plugin_settings import PluginSettings
from qgis_settings import QGISSettings

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'settings_dialog_base.ui'), from_imports=False)

class SettingsDialog(QtGui.QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
        # init form
        self.fill_pages()
        # signals
        self.btnGetContribPack.clicked.connect(self.get_contrib)
        self.accepted.connect(self.save_settings)

    def fill_pages(self):
        # common
        self.chkMoveToLayersMenu.setChecked(PluginSettings.move_to_layers_menu())
        self.chkEnableOTF3857.setChecked(PluginSettings.enable_otf_3857())
        self.chkShowMessagesInBar.setChecked(PluginSettings.show_messages_in_bar())
        # tiled layers
        self.spnConnCount.setValue(PluginSettings.default_tile_layer_conn_count())
        self.spnCacheExp.setValue(QGISSettings.get_default_tile_expiry())
        self.spnNetworkTimeout.setValue(QGISSettings.get_default_network_timeout())
        # contrib pack

    def save_settings(self):
        # common
        PluginSettings.set_move_to_layers_menu(self.chkMoveToLayersMenu.isChecked())
        PluginSettings.set_enable_otf_3857(self.chkEnableOTF3857.isChecked())
        PluginSettings.set_show_messages_in_bar(self.chkShowMessagesInBar.isChecked())
        # tiled layers
        PluginSettings.set_default_tile_layer_conn_count(self.spnConnCount.value())
        QGISSettings.set_default_tile_expiry(self.spnCacheExp.value())
        QGISSettings.set_default_network_timeout(self.spnNetworkTimeout.value())
        # contrib pack

    def apply_settings(self):
        pass

    def get_contrib(self):
        QgsApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        try:
            ExtraSources().load_contrib_pack()
            QgsApplication.restoreOverrideCursor()
            info_message = self.tr('Last version of contrib pack was downloaded!')
            QMessageBox.information(self, PluginSettings.product_name(), info_message)
        except:
            QgsApplication.restoreOverrideCursor()
            error_message = self.tr('Error on getting contrib pack: %s %s') % (sys.exc_type, sys.exc_value)
            QMessageBox.critical(self, PluginSettings.product_name(), error_message)
