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
from pathlib import Path
from typing import Dict, List, Optional

from quick_map_services.core.logging import logger
from quick_map_services.data_source_info import DataSourceCategory
from quick_map_services.data_source_serializer import DataSourceSerializer
from quick_map_services.group_info import GroupInfo
from quick_map_services.groups_list import GroupsList
from quick_map_services.paths_constants import (
    ALL_DS_PATHS,
    BASE_DATA_SOURCES_PATH,
)


class DataSourcesList:
    """
    Manage a collection of data sources loaded from configuration files.

    This class scans specified directories for ``.ini`` files describing
    data sources, parses them into :class:`DataSource` objects.
    """

    def __init__(
        self,
        ds_paths: List[Path] = ALL_DS_PATHS,
        group_info_map: Optional[Dict[str, GroupInfo]] = None,
    ) -> None:
        """
        Initialize the DataSourcesList and load available data sources.

        :param ds_paths: List of directories to scan for data sources.
        :param group_info_map: Group metadata used to resolve fallback icons.
        """
        self.data_sources = {}
        self.ds_paths = ds_paths
        self.group_info_map = group_info_map
        self._fill_data_sources_list()

    def _fill_data_sources_list(self) -> None:
        """
        Populate the internal dictionary of available data sources by scanning
        all configured data source directories.

        :return: None
        :rtype: None
        """
        self.data_sources = {}
        group_info_map = self.group_info_map
        if group_info_map is None:
            group_info_map = GroupsList().groups

        for ds_path in self.ds_paths:
            if ds_path == BASE_DATA_SOURCES_PATH:
                category = DataSourceCategory.BASE
            else:
                category = DataSourceCategory.USER

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

                    ds.category = category

                    icon_path = ds.icon_path
                    if icon_path is None:
                        group_info = group_info_map.get(ds.group)
                        if group_info is not None:
                            icon_path = group_info.icon
                    ds.icon_path = icon_path

                    self.data_sources[ds.id] = ds
