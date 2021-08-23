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
from qgis.PyQt.QtWidgets import QMenu

from qgis.core import QgsMessageLog
from .config_reader_helper import ConfigReaderHelper
from . import extra_sources
from .custom_translator import CustomTranslator
from .group_info import GroupInfo, GroupCategory
from .plugin_locale import Locale
from .compat import configparser, get_file_dir
from .compat2qgis import message_log_levels


CURR_PATH = get_file_dir(__file__)

INTERNAL_GROUP_PATHS = [os.path.join(CURR_PATH, extra_sources.GROUPS_DIR_NAME), ]
CONTRIBUTE_GROUP_PATHS = [os.path.join(extra_sources.CONTRIBUTE_DIR_PATH, extra_sources.GROUPS_DIR_NAME), ]
USER_GROUP_PATHS = [os.path.join(extra_sources.USER_DIR_PATH, extra_sources.GROUPS_DIR_NAME), ]

ALL_GROUP_PATHS = INTERNAL_GROUP_PATHS + CONTRIBUTE_GROUP_PATHS + USER_GROUP_PATHS

ROOT_MAPPING = {
    INTERNAL_GROUP_PATHS[0]: GroupCategory.BASE,
    CONTRIBUTE_GROUP_PATHS[0]: GroupCategory.CONTRIB,
    USER_GROUP_PATHS[0]: GroupCategory.USER
}


class GroupsList(object):

    def __init__(self, group_paths=ALL_GROUP_PATHS):
        self.locale = Locale.get_locale()
        self.translator = CustomTranslator()
        self.paths = group_paths
        self.groups = {}
        self._fill_groups_list()

    def _fill_groups_list(self):
        self.groups = {}
        for gr_path in self.paths:
            if gr_path in ROOT_MAPPING.keys():
                category = ROOT_MAPPING[gr_path]
            else:
                category = GroupCategory.USER

            for root, dirs, files in os.walk(gr_path):
                for ini_file in [f for f in files if f.endswith('.ini')]:
                    self._read_ini_file(root, ini_file, category)

    def _read_ini_file(self, root, ini_file_path, category):
        try:
            ini_full_path = os.path.join(root, ini_file_path)
            parser = configparser.ConfigParser()
            with codecs.open(ini_full_path, 'r', 'utf-8') as ini_file:
                
                if hasattr(parser, "read_file"):
                    parser.read_file(ini_file)
                else:
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
            # set contrib&user
            self.groups[group_id] = GroupInfo(group_id, group_alias, group_icon_path, ini_full_path, group_menu, category)
        except Exception as e:
            error_message = self.tr('Group INI file can\'t be parsed: ') + e.message
            QgsMessageLog.logMessage(error_message, level=message_log_levels["Critical"])

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
        return self.translator.translate('QuickMapServices', message)
