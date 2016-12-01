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


class KNOWN_DRIVERS(object):
    WMS = 'WMS'
    TMS = 'TMS'
    GDAL = 'GDAL'
    WFS = 'WFS'
    GEOJSON = 'GeoJSON'

    ALL_DRIVERS = [
        WMS,
        TMS,
        GDAL,
        WFS,
        GEOJSON,
    ]

    # 'TiledWMS',
    # 'VirtualEarth',
    # 'WorldWind',
    # 'AGS'
