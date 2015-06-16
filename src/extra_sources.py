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
from plugin_settings import PluginSettings

LOCAL_SETTINGS_PATH = os.path.dirname(QgsApplication.qgisUserDbFilePath())
PLUGIN_SETTINGS_PATH = os.path.join(LOCAL_SETTINGS_PATH, PluginSettings.product_name())

CONTRIBUTE_DIR_PATH = os.path.join(PLUGIN_SETTINGS_PATH, 'Contribute')
USER_DIR_PATH = os.path.join(PLUGIN_SETTINGS_PATH, 'User')

DATA_SOURCES_DIR_NAME = 'data_sources'
GROUPS_DIR_NAME = 'groups'


class ExtraSources:

    @classmethod
    def check_extra_dirs(cls):
        if not os.path.exists(PLUGIN_SETTINGS_PATH):
            os.mkdir(PLUGIN_SETTINGS_PATH)
        if not os.path.exists(CONTRIBUTE_DIR_PATH):
            os.mkdir(CONTRIBUTE_DIR_PATH)
        if not os.path.exists(USER_DIR_PATH):
            os.mkdir(USER_DIR_PATH)

        for base_folder in (CONTRIBUTE_DIR_PATH, USER_DIR_PATH):
            ds_folder = os.path.join(base_folder, DATA_SOURCES_DIR_NAME)
            if not os.path.exists(ds_folder):
                os.mkdir(ds_folder)
            groups_folder = os.path.join(base_folder, GROUPS_DIR_NAME)
            if not os.path.exists(groups_folder):
                os.mkdir(groups_folder)

    @classmethod
    def load_contrib_pack(cls):
        cls.check_extra_dirs()
        pass