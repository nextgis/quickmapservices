# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapServices
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
from ConfigParser import ConfigParser
import codecs
import os
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtGui import QMenu, QIcon, QAction
from qgis.core import QgsMessageLog
from data_source import DataSource

CURR_PATH = os.path.dirname(__file__)
DS_PATHS = [
    os.path.join(CURR_PATH, 'data_sources'),
    os.path.join(CURR_PATH, 'data_sources_contrib'),
]


class DataSourceFactory():
    def __init__(self):
        self.data_sources = {}
        self._fill_data_sources_list()

    def _fill_data_sources_list(self):
        self.data_sources = {}
        for ds_path in DS_PATHS:
            for root, dirs, files in os.walk(ds_path):
                for ini_file in [f for f in files if f.endswith('.ini')]:
                    self._read_ini_file(root, ini_file)

    def _read_ini_file(self, root, ini_file_path):
        try:
            ini_file = codecs.open(os.path.join(root, ini_file_path), 'r', 'utf-8')

            parser = ConfigParser()
            parser.readfp(ini_file)

            ds = DataSource()

            ds.id = parser.get('general', 'id')
            ds.type = parser.get('general', 'type')
            ds.is_contrib = parser.get('general', 'is_contrib')
            ds.source_file = os.path.join(root, parser.get('general', 'source_file'))

            ds.group = parser.get('ui', 'group')
            ds.alias = parser.get('ui', 'alias')
            ds.icon = parser.get('ui', 'icon')

            ds.lic_name = parser.get('license', 'name')
            ds.lic_link = parser.get('license', 'link')
            ds.copyright_text = parser.get('license', 'copyright_text')
            ds.copyright_link = parser.get('license', 'copyright_link')
            ds.terms_of_use = parser.get('license', 'terms_of_use')

            #action
            ds.icon_path = os.path.join(root, ds.icon)
            ds.action = QAction(QIcon(ds.icon_path), self.tr(ds.alias), None)
            ds.action.setData(ds)
            #ds.action

            self.data_sources[ds.id] = ds

        except Exception, e:
            error_message = 'INI file can\'t be parsed: ' + e.message
            QgsMessageLog.logMessage(error_message, level=QgsMessageLog.CRITICAL)


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MapServices', message)

