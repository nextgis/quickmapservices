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
import ConfigParser
import os
from PyQt4 import uic
from PyQt4.QtGui import QDialog, QDialogButtonBox, QPixmap, QTextDocument

CURR_PATH = os.path.dirname(__file__)

FORM_CLASS, _ = uic.loadUiType(os.path.join(CURR_PATH, 'about_dialog_base.ui'))


class AboutDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(AboutDialog, self).__init__(parent)
        self.setupUi(self)

        self.btnHelp = self.buttonBox.button(QDialogButtonBox.Help)

        self.lblLogo.setPixmap(QPixmap(os.path.join(CURR_PATH, 'icons/mapservices.png')))

        cfg = ConfigParser.SafeConfigParser()
        cfg.read(os.path.join(os.path.dirname(__file__), 'metadata.txt'))
        version = cfg.get('general', 'version')

        self.lblVersion.setText(self.tr('Version: %s') % (version))
        doc = QTextDocument()
        doc.setHtml(self.getAboutText())
        self.textBrowser.setDocument(doc)
        self.textBrowser.setOpenExternalLinks(True)

    def getAboutText(self):
        return self.tr('<p>Collection of internet map services</p>'
                       '<p><strong>Developers:</strong> <a href="http://nextgis.org">NextGIS</a></p>'
                       '<p><strong>Issue tracker:</strong> <a href="https://github.com/nextgis/mapservices/issues">GitHub</a></p>'
                       '<p><strong>Source code:</strong> <a href="https://github.com/nextgis/mapservices">GitHub</a></p>')

