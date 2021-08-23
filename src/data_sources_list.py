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
from __future__ import absolute_import
import codecs
import os
import sys
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog
from .config_reader_helper import ConfigReaderHelper
from .custom_translator import CustomTranslator
from .data_source_info import DataSourceInfo, DataSourceCategory
from . import extra_sources
from .data_source_serializer import DataSourceSerializer
from .plugin_locale import Locale
from .supported_drivers import KNOWN_DRIVERS
from .compat import get_file_dir
from .compat2qgis import message_log_levels

CURR_PATH = get_file_dir(__file__)

INTERNAL_DS_PATHS = [os.path.join(CURR_PATH, extra_sources.DATA_SOURCES_DIR_NAME), ]
CONTRIBUTE_DS_PATHS = [os.path.join(extra_sources.CONTRIBUTE_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME), ]
USER_DS_PATHS = [os.path.join(extra_sources.USER_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME), ]

ALL_DS_PATHS = INTERNAL_DS_PATHS + CONTRIBUTE_DS_PATHS + USER_DS_PATHS

ROOT_MAPPING = {
    INTERNAL_DS_PATHS[0]: DataSourceCategory.BASE,
    CONTRIBUTE_DS_PATHS[0]: DataSourceCategory.CONTRIB,
    USER_DS_PATHS[0]: DataSourceCategory.USER
}

class DataSourcesList(object):

    def __init__(self, ds_paths=ALL_DS_PATHS):
        self.data_sources = {}
        self.ds_paths = ds_paths
        self._fill_data_sources_list()

    def _fill_data_sources_list(self):
        self.data_sources = {}
        for ds_path in self.ds_paths:
            for root, dirs, files in os.walk(ds_path):
                for ini_file in [f for f in files if f.endswith('.ini')]:
                    try:
                        ini_full_path = os.path.join(root, ini_file)
                        ds = DataSourceSerializer.read_from_ini(ini_full_path)

                        # set contrib&user
                        if ds_path in ROOT_MAPPING.keys():
                            ds.category = ROOT_MAPPING[ds_path]
                        else:
                            ds.category = DataSourceCategory.USER

                        # action
                        ds.action = QAction(QIcon(ds.icon_path), self.tr(ds.alias), None)
                        ds.action.setData(ds)

                        # append to array
                        self.data_sources[ds.id] = ds

                    except Exception as e:
                        error_message = 'INI file can\'t be parsed: ' + e.message
                        QgsMessageLog.logMessage(error_message, level=message_log_levels["Critical"])

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        try:
            message = str(message)
        except:
            return message
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return CustomTranslator().translate('QuickMapServices', message)

