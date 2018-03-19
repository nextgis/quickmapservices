# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AboutDialog
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

from qgis.PyQt import uic
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from .compat import configparser


CURR_PATH = os.path.dirname(__file__)

FORM_CLASS, _ = uic.loadUiType(os.path.join(CURR_PATH, 'about_dialog_base.ui'))


class AboutDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(AboutDialog, self).__init__(parent)
        self.setupUi(self)

        self.btnHelp = self.buttonBox.button(QDialogButtonBox.Help)

        self.lblLogo.setPixmap(QPixmap(os.path.join(CURR_PATH, 'icons/mapservices.png')))

        cfg = configparser.ConfigParser()
        cfg.read(os.path.join(os.path.dirname(__file__), 'metadata.txt'))
        version = cfg.get('general', 'version')

        self.lblVersion.setText(self.tr('Version: %s') % (version))

        self.tbInfo.setHtml(self.get_about_text())
        self.tbLicense.setPlainText(self.get_license_text())
        self.tb3rd.setHtml(self.get_3rd_text())


    def get_about_text(self):
        return self.tr('<p>Convenient list of basemaps + seach string for finding datasets and basemaps. Please contribute new services via <a href="http://qms.nextgis.com">http://qms.nextgis.com</a></p>'
                       '<p><strong>Developers:</strong> <a href="http://nextgis.com">NextGIS</a></p>'
                       '<p><strong>Issue tracker:</strong> <a href="https://github.com/nextgis/quickmapservices/issues">GitHub</a></p>'
                       '<p><strong>Source code:</strong> <a href="https://github.com/nextgis/quickmapservices">GitHub</a></p>')

    def get_license_text(self):
        with open(os.path.join(CURR_PATH, 'LICENSE')) as f:
            return f.read()

    def get_3rd_text(self):
        return self.tr('<p><strong>Python tile layer:</strong> <a href="https://github.com/minorua/TileLayerPlugin">TileLayer Plugin by Minoru Akagi</a></p>'
                       '<p><strong>Some icons from QGIS:</strong> <a href="https://github.com/qgis/QGIS">QGIS GitHub</a></p>')


