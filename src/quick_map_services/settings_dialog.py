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
import sys

from qgis.core import Qgis, QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

from .data_sources_model import DSManagerModel
from .extra_sources import ExtraSources
from .plugin_settings import PluginSettings
from .qgis_settings import QGISSettings

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "settings_dialog_base.ui"),
)


class SettingsDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
        self.tabUserServices.setCurrentIndex(0)
        # init form
        self.fill_pages()
        # init services visibility tab
        self.dsManagerViewModel = DSManagerModel()
        self.treeViewForDS.setModel(self.dsManagerViewModel)

        if hasattr(self.treeViewForDS.header(), "setResizeMode"):
            # Qt4
            self.treeViewForDS.header().setResizeMode(
                DSManagerModel.COLUMN_GROUP_DS, QHeaderView.ResizeMode.Stretch
            )  # !!! need to check
        else:
            # Qt5
            self.treeViewForDS.header().setSectionResizeMode(
                DSManagerModel.COLUMN_GROUP_DS, QHeaderView.ResizeMode.Stretch
            )  # !!! need to check

        showAllAction = self.toolBarForDSTreeView.addAction(
            QIcon(":/images/themes/default/mActionShowAllLayers.svg"), self.tr("Show all")
        )
        showAllAction.triggered.connect(self.dsManagerViewModel.checkAll)

        hideAllAction = self.toolBarForDSTreeView.addAction(
            QIcon(":images/themes/default/mActionHideAllLayers.svg"), self.tr("Hide all")
        )
        hideAllAction.triggered.connect(self.dsManagerViewModel.uncheckAll)
        self.dsManagerViewModel.sort(DSManagerModel.COLUMN_GROUP_DS)
        # signals
        self.btnGetContribPack.clicked.connect(self.get_contrib)
        self.accepted.connect(self.save_settings)

    def fill_pages(self):
        # common
        self.chkEnableOTF3857.setChecked(PluginSettings.enable_otf_3857())
        self.chkShowMessagesInBar.setChecked(
            PluginSettings.show_messages_in_bar()
        )
        # tiled layers
        self.spnConnCount.setValue(
            PluginSettings.default_tile_layer_conn_count()
        )
        self.spnCacheExp.setValue(QGISSettings.get_default_tile_expiry())
        self.spnNetworkTimeout.setValue(
            QGISSettings.get_default_network_timeout()
        )
        
        # Native renderer options (hidden for now)
        self.useNativeRenderer2188AndHigherLabel.setVisible(False)
        self.chkUseNativeRenderer.setChecked(True)
        self.chkUseNativeRenderer.setEnabled(False)
        self.chkUseNativeRenderer.setVisible(False)

        # contrib pack

    def save_settings(self):
        # common
        PluginSettings.set_enable_otf_3857(self.chkEnableOTF3857.isChecked())
        PluginSettings.set_show_messages_in_bar(
            self.chkShowMessagesInBar.isChecked()
        )
        # tiled layers
        PluginSettings.set_default_tile_layer_conn_count(
            self.spnConnCount.value()
        )
        QGISSettings.set_default_tile_expiry(self.spnCacheExp.value())
        QGISSettings.set_default_network_timeout(
            self.spnNetworkTimeout.value()
        )
        # contrib pack

        # ds visibility
        self.dsManagerViewModel.saveSettings()

    def apply_settings(self):
        pass

    def get_contrib(self):
        QgsApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        try:
            ExtraSources().load_contrib_pack()
            QgsApplication.restoreOverrideCursor()
            info_message = self.tr(
                "Last version of contrib pack was downloaded!"
            )
            QMessageBox.information(
                self, PluginSettings.product_name(), info_message
            )

            self.dsManagerViewModel.resetModel()
        except Exception as e:
            QgsApplication.restoreOverrideCursor()
            error_message = self.tr("Error on getting contrib pack: %s") % str(
                e
            )
            QMessageBox.critical(
                self, PluginSettings.product_name(), error_message
            )
