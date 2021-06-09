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
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsNetworkAccessManager


class QGISSettings(object):

    NEW_PROJECT_USE_PRESET_CRS = 'UsePresetCrs'

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

    @classmethod
    def get_qgis_proxy(cls):
        s = cls.get_settings()
        proxy_enabled = s.value("proxy/proxyEnabled", u"", type=unicode)
        proxy_type = s.value("proxy/proxyType", u"", type=unicode)
        proxy_host = s.value("proxy/proxyHost", u"", type=unicode)
        proxy_port = s.value("proxy/proxyPort", u"", type=unicode)
        proxy_user = s.value("proxy/proxyUser", u"", type=unicode)
        proxy_password = s.value("proxy/proxyPassword", u"", type=unicode)

        if proxy_enabled == "true":
            if proxy_type == "DefaultProxy":
                qgsNetMan = QgsNetworkAccessManager.instance()
                proxy = qgsNetMan.proxy().applicationProxy()
                proxy_host = proxy.hostName()
                proxy_port = str(proxy.port())
                proxy_user = proxy.user()
                proxy_password = proxy.password()

            if proxy_type in ["DefaultProxy", "Socks5Proxy", "HttpProxy", "HttpCachingProxy"]:
                return (
                    proxy_host,
                    proxy_port,
                    proxy_user,
                    proxy_password
                )

        return ("", "", "", "")

    @classmethod
    def get_new_project_crs_behavior(cls, def_value=''):
        return QGISSettings.get_settings().value('/app/projections/newProjectCrsBehavior', def_value, type=str)