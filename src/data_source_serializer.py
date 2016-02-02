import codecs
import os
from ConfigParser import ConfigParser

from config_reader_helper import ConfigReaderHelper
from custom_translator import CustomTranslator
from data_source_info import DataSourceInfo
from locale import Locale
from supported_drivers import KNOWN_DRIVERS


class DataSourceSerializer():

    @classmethod
    def read_from_ini(cls, ini_file_path):
        translator = CustomTranslator()
        locale = Locale.get_locale()

        dir_path = os.path.abspath(os.path.join(ini_file_path, os.path.pardir))
        ini_file = codecs.open(ini_file_path, 'r', 'utf-8')

        parser = ConfigParser()
        parser.readfp(ini_file)

        ds = DataSourceInfo()

        # Required
        ds.id = ConfigReaderHelper.try_read_config(parser, 'general', 'id', reraise=True)
        ds.type = ConfigReaderHelper.try_read_config(parser, 'general', 'type', reraise=True)

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
            ds.gdal_source_file = os.path.join(dir_path, gdal_conf)

        #try read translations
        posible_trans = parser.items('ui')
        for key, val in posible_trans:
            if type(key) is unicode and key == 'alias[%s]' % locale:
                translator.append(ds.alias, val)
                break

        #internal stuff
        ds.file_path = ini_file_path
        ds.icon_path = os.path.join(dir_path, ds.icon) if ds.icon else None

        return ds
