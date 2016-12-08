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
from .supported_drivers import KNOWN_DRIVERS

try:
    from osgeo import gdal
except ImportError:
    import gdal


class GdalUtils(object):

    @classmethod
    def get_supported_drivers(cls):
        formats_list = []
        cnt = gdal.GetDriverCount()
        for i in range(cnt):
            driver = gdal.GetDriver(i)
            driver_name = driver.ShortName
            if not driver_name in formats_list:
                formats_list.append(driver_name)
        if 'WMS' in formats_list:
            return KNOWN_DRIVERS  # all drivers if wms supported. hack. need to remake