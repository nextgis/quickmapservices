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
from ConfigParser import ConfigParser
import codecs
import os
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtGui import QIcon, QAction
from qgis.core import QgsMessageLog
from data_source_info import DataSourceInfo
from supported_drivers import KNOWN_DRIVERS

CURR_PATH = os.path.dirname(__file__)
DS_PATHS = [
    os.path.join(CURR_PATH, 'data_sources'),
    os.path.join(CURR_PATH, 'data_sources_contrib'),
]


class DataSourcesList():
    def __init__(self, locale, custom_translator):
        self.locale = locale  # for translation
        self.translator = custom_translator
        self.data_sources = {}
        self._fill_data_sources_list()

    def _fill_data_sources_list(self):
        self.data_sources = {}
        for ds_path in DS_PATHS:
            for root, dirs, files in os.walk(ds_path):
                for ini_file in [f for f in files if f.endswith('.ini')]:
                    self._read_ini_file(root, ini_file)

    def _read_ini_file(self, root, ini_file_path):
        try:
            ini_file = codecs.open(os.path.join(root, ini_file_path), 'r', 'utf-8')

            parser = ConfigParser()
            parser.readfp(ini_file)

            ds = DataSourceInfo()

            # Required
            ds.id = self.try_read_config(parser, 'general', 'id', reraise=True)
            ds.type = self.try_read_config(parser, 'general', 'type', reraise=True)
            ds.is_contrib = self.try_read_config(parser, 'general', 'is_contrib', reraise=True)

            ds.group = self.try_read_config(parser, 'ui', 'group', reraise=True)
            ds.alias = self.try_read_config(parser, 'ui', 'alias', reraise=True)
            ds.icon = self.try_read_config(parser, 'ui', 'icon', reraise=True)

            # Lic & Terms
            ds.lic_name = self.try_read_config(parser, 'license', 'name')
            ds.lic_link = self.try_read_config(parser, 'license', 'link')
            ds.copyright_text = self.try_read_config(parser, 'license', 'copyright_text')
            ds.copyright_link = self.try_read_config(parser, 'license', 'copyright_link')
            ds.terms_of_use = self.try_read_config(parser, 'license', 'terms_of_use')

            #TMS
            ds.tms_url = self.try_read_config(parser, 'tms', 'url', reraise=(ds.type == KNOWN_DRIVERS.TMS))
            ds.tms_zmin = self.try_read_config_int(parser, 'tms', 'zmin')
            ds.tms_zmax = self.try_read_config_int(parser, 'tms', 'zmax')

            #WMS
            ds.wms_url = self.try_read_config(parser, 'wms', 'url', reraise=(ds.type == KNOWN_DRIVERS.WMS))
            ds.wms_params = self.try_read_config(parser, 'wms', 'params')
            ds.wms_layers = self.try_read_config(parser, 'wms', 'layers')

            #GDAL
            if ds.type == KNOWN_DRIVERS.GDAL:
                gdal_conf = self.try_read_config(parser, 'gdal', 'source_file', reraise=(ds.type == KNOWN_DRIVERS.GDAL))
                ds.gdal_source_file = os.path.join(root, gdal_conf)

            #try read translations
            posible_trans = parser.items('ui')
            for key, val in posible_trans:
                if type(key) is unicode and key == 'alias[%s]' % self.locale:
                    self.translator.append(ds.alias, val)
                    break

            #Action stuff
            ds.icon_path = os.path.join(root, ds.icon)
            ds.action = QAction(QIcon(ds.icon_path), self.tr(ds.alias), None)
            ds.action.setData(ds)

            #append to array
            self.data_sources[ds.id] = ds

        except Exception, e:
            error_message = 'INI file can\'t be parsed: ' + e.message
            QgsMessageLog.logMessage(error_message, level=QgsMessageLog.CRITICAL)


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QuickMapServices', message)

    def try_read_config(self, parser, section, param, reraise=False):
        try:
            val = parser.get(section, param)
        except:
            if reraise:
                raise
            else:
                val = None
        return val

    def try_read_config_int(self, parser, section, param, reraise=False):
        try:
            val = parser.getint(section, param)
        except:
            if reraise:
                raise
            else:
                val = None
        return val