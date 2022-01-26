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
import re
import itertools


class DataSourceCategory(object):
    BASE = 'base'
    CONTRIB = 'contributed'
    USER = 'user'

    all = [BASE, CONTRIB, USER]


class DataSourceInfo(object):

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

        self.__tms_url = None
        self.__alt_tms_url = None
        self.tms_zmin = None
        self.tms_zmax = None
        self.tms_y_origin_top = None
        self.tms_epsg_crs_id = None
        self.tms_postgis_crs_id = None
        self.tms_custom_proj = None
        self.tms_tile_ranges = None
        self.tms_tsize1 = None
        self.tms_origin_x = None
        self.tms_origin_y = None

        self.wms_url = None
        self.wms_params = None
        self.wms_url_params = None
        self.wms_layers = None
        self.wms_turn_over = None

        self.gdal_source_file = None

        self.wfs_url = None
        self.wfs_layers = []
        self.wfs_params = None
        self.wfs_epsg = None
        self.wfs_turn_over = None

        self.geojson_url = None

        # internal
        self.file_path = None
        self.icon_path = None
        self.action = None
        self.category = None

    def _parse_tms_url(self, url):
        if url is None:
            return []

        url = url.replace('%', '%%') #escaping percent symbols before string formatting below

        switch_re = r"{switch:[^\}]*}"
        switches = re.findall(switch_re, url)

        url_pattern = url
        for switch in switches:
            url_pattern = url_pattern.replace(switch, '%s', 1)

        switch_variants = []
        for switch in switches:
            switch_variants.append(switch[8:-1].split(','))

        urls = []
        for variants in list(itertools.product(*switch_variants)):
            urls.append(
                url_pattern % variants
            )
        return urls

    @property
    def tms_url(self):
        return self.__tms_url

    @tms_url.setter
    def tms_url(self, url):
        self.__tms_url = url
        self.__alt_tms_url = self._parse_tms_url(self.__tms_url)
    @property
    def alt_tms_urls(self):
        return self.__alt_tms_url 
