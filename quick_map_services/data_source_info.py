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


class DataSourceCategory:
    BASE = 'base'
    CONTRIB = 'contributed'
    USER = 'user'

    all = [BASE, CONTRIB, USER]


class DataSourceInfo:

    def __init__(self):
        self.id = None
        self.type = None

        self.group = None
        self.alias = None
        self.icon = None

        self.lic_name = None
        self.lic_link = None
        self.copyright_text = None
        self.copyright_link = None
        self.terms_of_use = None

        self.tms_url = None
        self.tms_zmin = None
        self.tms_zmax = None
        self.tms_y_origin_top = None
        self.tms_epsg_crs_id = None
        self.tms_postgis_crs_id = None
        self.tms_custom_proj = None

        self.wms_url = None
        self.wms_params = None
        self.wms_layers = None
        self.wms_turn_over = None

        self.gdal_source_file = None

        self.wfs_url = None
        # self.wfs_layers = None

        # internal
        self.file_path = None
        self.icon_path = None
        self.action = None
        self.category = None
