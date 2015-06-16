# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Common Plugins settings

 NextGIS
                             -------------------
        begin                : 2014-10-31
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
from PyQt4.QtCore import QSettings


class QGISSettings():

    @classmethod
    def get_settings(cls):
        return QSettings()

    @classmethod
    def get_default_tile_expiry(self, def_value=24):
        return QGISSettings.get_settings().value('/qgis/defaultTileExpiry', def_value, type=int)

    @classmethod
    def set_default_tile_expiry(self, int_value):
        if not isinstance(int_value, int) or int_value < 0 or int_value > 100000000:
            raise ValueError(int_value)
        return QGISSettings.get_settings().setValue('/qgis/defaultTileExpiry', int_value)

    @classmethod
    def get_default_user_agent(self, def_value='Mozilla/5.0'):
        return QGISSettings.get_settings().value('/qgis/networkAndProxy/userAgent', def_value, type=str)

    @classmethod
    def set_default_user_agent(self, str_value):
        if not str_value:
            raise ValueError(str_value)
        return QGISSettings.get_settings().setValue('/qgis/networkAndProxy/userAgent', str_value)

    @classmethod
    def get_default_network_timeout(self, def_value=60000):
        return QGISSettings.get_settings().value('/qgis/networkAndProxy/networkTimeout', def_value, type=int)

    @classmethod
    def set_default_network_timeout(self, int_value):
        if not isinstance(int_value, int) or int_value < 1 or int_value > 100000000:
            raise ValueError(int_value)
        return QGISSettings.get_settings().setValue('/qgis/networkAndProxy/networkTimeout', int_value)