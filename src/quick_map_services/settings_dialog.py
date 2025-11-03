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

from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *

from quick_map_services.core.settings import QmsSettings

from .data_sources_model import DSManagerModel
from .extra_sources import ExtraSources

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
            QIcon(":/images/themes/default/mActionShowAllLayers.svg"),
            self.tr("Show all"),
        )
        showAllAction.triggered.connect(self.dsManagerViewModel.checkAll)

        hideAllAction = self.toolBarForDSTreeView.addAction(
            QIcon(":images/themes/default/mActionHideAllLayers.svg"),
            self.tr("Hide all"),
        )
        hideAllAction.triggered.connect(self.dsManagerViewModel.uncheckAll)
        self.dsManagerViewModel.sort(DSManagerModel.COLUMN_GROUP_DS)
        # signals
        self.btnGetContribPack.clicked.connect(self.get_contrib)
        self.accepted.connect(self.save_settings)

    def fill_pages(self):
        settings = QmsSettings()

        # common
        self.chkEnableOTF3857.setChecked(settings.enable_otf_3857)
        self.chkShowMessagesInBar.setChecked(settings.show_messages_in_bar)

        # contrib pack

    def save_settings(self):
        settings = QmsSettings()

        # common
        settings.enable_otf_3857 = self.chkEnableOTF3857.isChecked()
        settings.show_messages_in_bar = self.chkShowMessagesInBar.isChecked()

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
            QMessageBox.information(self, QmsSettings.PRODUCT, info_message)

            self.dsManagerViewModel.resetModel()
        except Exception as error:
            QgsApplication.restoreOverrideCursor()
            error_message = self.tr("Error on getting contrib pack: %s") % str(
                error
            )
            QMessageBox.critical(self, QmsSettings.PRODUCT, error_message)
