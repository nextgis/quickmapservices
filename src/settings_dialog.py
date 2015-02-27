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
from plugin_settings import PluginSettings

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'settings_dialog_base.ui'))


class SettingsDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)

        self.fill_common_page()
        self.fill_tiled_lyr_page()
        self.fill_contrib_pack_page()
        self.btnGetContribPack.clicked.connect(self.get_contrib)
        self.accepted.connect(self.save_settings)

    def fill_common_page(self):
        self.chkMoveToLayersMenu.setChecked(PluginSettings.move_to_layers_menu())
        self.chkEnableOTF3857.setChecked(PluginSettings.enable_otf_3857())
        self.chkShowMessagesInBar.setChecked(PluginSettings.show_messages_in_bar())

    def fill_tiled_lyr_page(self):
        self.spnConnCount.setValue(PluginSettings.default_tile_layer_conn_count())

    def fill_contrib_pack_page(self):
        pass

    def get_contrib(self):
        pass

    def save_settings(self):
        # common
        PluginSettings.set_move_to_layers_menu(self.chkMoveToLayersMenu.checked())
        PluginSettings.set_enable_otf_3857(self.chkEnableOTF3857.checked())
        PluginSettings.set_show_messages_in_bar(self.chkShowMessagesInBar.checked())

        #tiled layers
        PluginSettings.set_default_tile_layer_conn_count(self.spnConnCount.value())

