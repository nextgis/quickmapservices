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
from config_reader_helper import ConfigReaderHelper
from custom_translator import CustomTranslator
from data_source_info import DataSourceInfo
import extra_sources
from locale import Locale
from supported_drivers import KNOWN_DRIVERS

CURR_PATH = os.path.dirname(__file__)

INTERNAL_DS_PATHS = [os.path.join(CURR_PATH, extra_sources.DATA_SOURCES_DIR_NAME), ]
CONTRIBUTE_DS_PATHS = [os.path.join(extra_sources.CONTRIBUTE_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME), ]
USER_DS_PATHS = [os.path.join(extra_sources.USER_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME), ]


ALL_DS_PATHS = INTERNAL_DS_PATHS + CONTRIBUTE_DS_PATHS + USER_DS_PATHS


class DataSourcesList:

    def __init__(self, ds_paths=ALL_DS_PATHS):
        self.locale = Locale.get_locale()
        self.translator = CustomTranslator()
        self.data_sources = {}
        self.ds_paths = ds_paths
        self._fill_data_sources_list()

    def _fill_data_sources_list(self):
        self.data_sources = {}
        for ds_path in self.ds_paths:
            for root, dirs, files in os.walk(ds_path):
                for ini_file in [f for f in files if f.endswith('.ini')]:
                    self._read_ini_file(root, ini_file)

    def _read_ini_file(self, root, ini_file_path):
        try:
            ini_full_path = os.path.join(root, ini_file_path)
            ini_file = codecs.open(ini_full_path, 'r', 'utf-8')

            parser = ConfigParser()
            parser.readfp(ini_file)

            ds = DataSourceInfo()

            # Required
            ds.id = ConfigReaderHelper.try_read_config(parser, 'general', 'id', reraise=True)
            ds.type = ConfigReaderHelper.try_read_config(parser, 'general', 'type', reraise=True)
            ds.is_contrib = ConfigReaderHelper.try_read_config(parser, 'general', 'is_contrib', reraise=True)

            ds.group = ConfigReaderHelper.try_read_config(parser, 'ui', 'group', reraise=True)
            ds.alias = ConfigReaderHelper.try_read_config(parser, 'ui', 'alias', reraise=True)
            ds.icon = ConfigReaderHelper.try_read_config(parser, 'ui', 'icon')

            # Lic & Terms
            ds.lic_name = ConfigReaderHelper.try_read_config(parser, 'license', 'name')
            ds.lic_link = ConfigReaderHelper.try_read_config(parser, 'license', 'link')
            ds.copyright_text = ConfigReaderHelper.try_read_config(parser, 'license', 'copyright_text')
            ds.copyright_link = ConfigReaderHelper.try_read_config(parser, 'license', 'copyright_link')
            ds.terms_of_use = ConfigReaderHelper.try_read_config(parser, 'license', 'terms_of_use')

            #TMS
            ds.tms_url = ConfigReaderHelper.try_read_config(parser, 'tms', 'url', reraise=(ds.type == KNOWN_DRIVERS.TMS))
            ds.tms_zmin = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'zmin')
            ds.tms_zmax = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'zmax')
            ds.tms_y_origin_top = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'y_origin_top')
            ds.tms_epsg_crs_id = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'epsg_crs_id')
            ds.tms_postgis_crs_id = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'postgis_crs_id')
            ds.tms_custom_proj = ConfigReaderHelper.try_read_config(parser, 'tms', 'custom_proj')

            #WMS
            ds.wms_url = ConfigReaderHelper.try_read_config(parser, 'wms', 'url', reraise=(ds.type == KNOWN_DRIVERS.WMS))
            ds.wms_params = ConfigReaderHelper.try_read_config(parser, 'wms', 'params')
            ds.wms_layers = ConfigReaderHelper.try_read_config(parser, 'wms', 'layers')
            ds.wms_turn_over = ConfigReaderHelper.try_read_config_bool(parser, 'wms', 'turn_over')

            #GDAL
            if ds.type == KNOWN_DRIVERS.GDAL:
                gdal_conf = ConfigReaderHelper.try_read_config(parser, 'gdal', 'source_file', reraise=(ds.type == KNOWN_DRIVERS.GDAL))
                ds.gdal_source_file = os.path.join(root, gdal_conf)

            #try read translations
            posible_trans = parser.items('ui')
            for key, val in posible_trans:
                if type(key) is unicode and key == 'alias[%s]' % self.locale:
                    self.translator.append(ds.alias, val)
                    break

            #Action and internal stuff
            ds.file_path = ini_full_path
            ds.icon_path = os.path.join(root, ds.icon) if ds.icon else None
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

