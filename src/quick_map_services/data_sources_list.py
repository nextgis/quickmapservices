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

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from quick_map_services.core.logging import logger

from . import extra_sources
from .custom_translator import CustomTranslator
from .data_source_info import DataSourceCategory
from .data_source_serializer import DataSourceSerializer

CURR_PATH = os.path.dirname(__file__)

INTERNAL_DS_PATHS = [
    os.path.join(CURR_PATH, extra_sources.DATA_SOURCES_DIR_NAME),
]
CONTRIBUTE_DS_PATHS = [
    os.path.join(
        extra_sources.CONTRIBUTE_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME
    ),
]
USER_DS_PATHS = [
    os.path.join(
        extra_sources.USER_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME
    ),
]

ALL_DS_PATHS = INTERNAL_DS_PATHS + CONTRIBUTE_DS_PATHS + USER_DS_PATHS

ROOT_MAPPING = {
    INTERNAL_DS_PATHS[0]: DataSourceCategory.BASE,
    CONTRIBUTE_DS_PATHS[0]: DataSourceCategory.CONTRIB,
    USER_DS_PATHS[0]: DataSourceCategory.USER,
}


class DataSourcesList:
    def __init__(self, ds_paths=ALL_DS_PATHS):
        self.data_sources = {}
        self.ds_paths = ds_paths
        self._fill_data_sources_list()

    def _fill_data_sources_list(self) -> None:
        """
        Populate the internal dictionary of available data sources by scanning
        all configured data source directories.

        :return: None
        :rtype: None
        """
        self.data_sources = {}
        for ds_path in self.ds_paths:
            for root, _dirs, files in os.walk(ds_path):
                ini_files = [file for file in files if file.endswith(".ini")]

                for ini_file in ini_files:
                    ini_full_path = os.path.join(root, ini_file)

                    try:
                        ds = DataSourceSerializer.read_from_ini(ini_full_path)
                    except Exception:
                        logger.exception(
                            f"Failed to parse INI file: {ini_full_path}"
                        )
                        continue

                    ds.category = ROOT_MAPPING.get(
                        ds_path, DataSourceCategory.USER
                    )

                    ds.action = QAction(
                        QIcon(ds.icon_path), self.tr(ds.alias), None
                    )
                    ds.action.setData(ds)

                    self.data_sources[ds.id] = ds

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        try:
            message = str(message)
        except:
            return message
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return CustomTranslator().translate("QuickMapServices", message)
