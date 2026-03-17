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
import configparser
import os
from pathlib import Path
from typing import List

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMenu

from quick_map_services.config_reader_helper import ConfigReaderHelper
from quick_map_services.core import utils
from quick_map_services.core.logging import logger
from quick_map_services.custom_translator import CustomTranslator
from quick_map_services.group_info import GroupCategory, GroupInfo
from quick_map_services.paths_constants import (
    ALL_GROUP_PATHS,
    BASE_GROUPS_PATH,
)


class GroupsList:
    """
    Manage a collection of groups loaded from configuration files.

    This class scans specified directories for ``.ini`` files describing
    groups, parses their metadata, and stores them as :class:`GroupInfo`
    objects.
    """

    def __init__(self, group_paths: List[Path] = ALL_GROUP_PATHS) -> None:
        """
        Initialize the GroupsList instance and load group definitions.

        :param group_paths: List of directory paths to search for group
            definition files.
        """
        self.translator = CustomTranslator()
        self.paths = group_paths
        self.groups = {}
        self._fill_groups_list()

    def _fill_groups_list(self) -> None:
        """
        Populate the internal groups dictionary from configuration files.

        :returns: None
        """
        self.groups = {}
        for gr_path in self.paths:
            if gr_path == BASE_GROUPS_PATH:
                category = GroupCategory.BASE
            else:
                category = GroupCategory.USER

            for root, _dirs, files in os.walk(gr_path):
                for ini_file in [f for f in files if f.endswith(".ini")]:
                    self._read_ini_file(root, ini_file, category)

    def _read_ini_file(
        self, root: str, ini_file_path: str, category: str
    ) -> None:
        """
        Parse a group definition `.ini` file and register it in the internal group list.

        This method reads the provided `.ini` configuration file, extracts general and
        UI-related metadata such as group ID, alias, and icon path, and creates a
        corresponding `GroupInfo` object representing the group.

        :param root: The root directory path where the `.ini` file is located.
        :type root: str
        :param ini_file_path: The name of the `.ini` file to be parsed.
        :type ini_file_path: str
        :param category: The category of the group (e.g., BASE, USER).
        :type category: str

        :return: None
        :rtype: None
        """
        ini_full_path = os.path.join(root, ini_file_path)

        try:
            parser = configparser.ConfigParser()
            with codecs.open(ini_full_path, "r", "utf-8") as ini_file:
                if hasattr(parser, "read_file"):
                    parser.read_file(ini_file)
                else:
                    parser.readfp(ini_file)

            # Extract group metadata
            group_id = parser.get("general", "id")
            group_alias = parser.get("ui", "alias")
            icon_file = ConfigReaderHelper.try_read_config(
                parser, "ui", "icon"
            )
            group_icon_path = (
                os.path.join(root, icon_file) if icon_file else None
            )

            # Read possible translations
            posible_trans = parser.items("ui")
            for key, val in posible_trans:
                if key == f"alias[{utils.locale()}]":
                    self.translator.append(group_alias, val)
                    break

        except Exception:
            logger.exception(
                f"Failed to parse group INI file: {ini_full_path}"
            )
            return

        # Create QMenu and GroupInfo
        group_menu = QMenu(self.tr(group_alias))
        group_menu.setIcon(QIcon(group_icon_path))

        self.groups[group_id] = GroupInfo(
            group_id,
            group_alias,
            group_icon_path,
            ini_full_path,
            group_menu,
            category,
        )

    def get_group_menu(self, group_id: str) -> QMenu:
        """
        Retrieve or create a QMenu for the specified group.

        :param group_id: Unique identifier of the group.

        :returns: QMenu instance associated with the group.
        """
        if group_id in self.groups:
            return self.groups[group_id].menu
        else:
            info = GroupInfo(group_id=group_id, menu=QMenu(group_id))
            self.groups[group_id] = info
            return info.menu

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return self.translator.translate("QuickMapServices", message)
