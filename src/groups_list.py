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
import codecs
import os
from ConfigParser import ConfigParser
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtGui import QMenu, QIcon
from qgis.core import QgsMessageLog
from config_reader_helper import ConfigReaderHelper
import extra_sources
from custom_translator import CustomTranslator
from group_info import GroupInfo
from locale import Locale

CURR_PATH = os.path.dirname(__file__)

INTERNAL_GROUP_PATHS = [os.path.join(CURR_PATH, extra_sources.GROUPS_DIR_NAME), ]
CONTRIBUTE_GROUP_PATHS = [os.path.join(extra_sources.CONTRIBUTE_DIR_PATH, extra_sources.GROUPS_DIR_NAME), ]
USER_GROUP_PATHS = [os.path.join(extra_sources.USER_DIR_PATH, extra_sources.GROUPS_DIR_NAME), ]

ALL_GROUP_PATHS = INTERNAL_GROUP_PATHS + CONTRIBUTE_GROUP_PATHS + USER_GROUP_PATHS


class GroupsList:

    def __init__(self, group_paths=ALL_GROUP_PATHS):
        self.locale = Locale.get_locale()
        self.translator = CustomTranslator()
        self.paths = group_paths
        self.groups = {}
        self._fill_groups_list()

    def _fill_groups_list(self):
        self.groups = {}
        for gr_path in self.paths:
            for root, dirs, files in os.walk(gr_path):
                for ini_file in [f for f in files if f.endswith('.ini')]:
                    self._read_ini_file(root, ini_file)

    def _read_ini_file(self, root, ini_file_path):
        try:
            ini_full_path = os.path.join(root, ini_file_path)
            parser = ConfigParser()
            ini_file = codecs.open(ini_full_path, 'r', 'utf-8')
            parser.readfp(ini_file)
            #read config
            group_id = parser.get('general', 'id')
            group_alias = parser.get('ui', 'alias')
            icon_file = ConfigReaderHelper.try_read_config(parser, 'ui', 'icon')
            group_icon_path = os.path.join(root, icon_file) if icon_file else None
            #try read translations
            posible_trans = parser.items('ui')
            for key, val in posible_trans:
                if type(key) is unicode and key == 'alias[%s]' % self.locale:
                    self.translator.append(group_alias, val)
                    break
            #create menu
            group_menu = QMenu(self.tr(group_alias))
            group_menu.setIcon(QIcon(group_icon_path))
            #append to all groups
            self.groups[group_id] = GroupInfo(group_id, group_alias, group_icon_path, ini_full_path, group_menu)
        except Exception, e:
            error_message = self.tr('Group INI file can\'t be parsed: ') + e.message
            QgsMessageLog.logMessage(error_message, level=QgsMessageLog.CRITICAL)

    def get_group_menu(self, group_id):
        if group_id in self.groups:
            return self.groups[group_id].menu
        else:
            info = GroupInfo(group_id=group_id, menu=QMenu(group_id))
            self.groups[group_id] = info
            return info.menu

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QuickMapServices', message)