import codecs
import os
from ConfigParser import ConfigParser
from config_reader_helper import ConfigReaderHelper
from custom_translator import CustomTranslator
from data_source_info import DataSourceInfo
from fixed_config_parser import FixedConfigParser
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
        ds.tms_custom_tile_ranges = ConfigReaderHelper.try_read_config(parser, 'tms', 'custom_tile_ranges')
        ds.tms_custom_tsize1 = ConfigReaderHelper.try_read_config_float(parser, 'tms', 'custom_tsize1')
        ds.tms_custom_origin_x = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'custom_origin_x')
        ds.tms_custom_origin_y = ConfigReaderHelper.try_read_config_int(parser, 'tms', 'custom_origin_y')

        #WMS
        ds.wms_url = ConfigReaderHelper.try_read_config(parser, 'wms', 'url', reraise=(ds.type == KNOWN_DRIVERS.WMS))
        ds.wms_params = ConfigReaderHelper.try_read_config(parser, 'wms', 'params')
        ds.wms_layers = ConfigReaderHelper.try_read_config(parser, 'wms', 'layers')
        ds.wms_turn_over = ConfigReaderHelper.try_read_config_bool(parser, 'wms', 'turn_over')

        #GDAL
        if ds.type == KNOWN_DRIVERS.GDAL:
            gdal_conf = ConfigReaderHelper.try_read_config(parser, 'gdal', 'source_file', reraise=(ds.type == KNOWN_DRIVERS.GDAL))
            ds.gdal_source_file = os.path.join(dir_path, gdal_conf)

        #WFS
        ds.wfs_url = ConfigReaderHelper.try_read_config(parser, 'wfs', 'url', reraise=(ds.type == KNOWN_DRIVERS.WFS))
        # ds.wfs_layers = ConfigReaderHelper.try_read_config(parser, 'wfs', 'layers')

        # WFS
        ds.geojson_url = ConfigReaderHelper.try_read_config(parser, 'geojson', 'url', reraise=(ds.type == KNOWN_DRIVERS.GEOJSON))

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

    @classmethod
    def read_from_json(cls, json_data):
        ds = DataSourceInfo()

        # Required
        ds.id = json_data['id']
        ds.type = json_data['type']

        ds.group = None
        ds.alias = json_data['name']
        ds.icon = None

        # Lic & Terms
        ds.lic_name = json_data['license_name']
        ds.lic_link = json_data['license_url']
        ds.copyright_text = json_data['copyright_text']
        ds.copyright_link = json_data['copyright_url']
        ds.terms_of_use = json_data['terms_of_use_url']

        #TMS
        if ds.type.lower() == KNOWN_DRIVERS.TMS.lower():
            ds.tms_url = json_data['url']
            ds.tms_zmin = json_data['z_min']
            ds.tms_zmax = json_data['z_max']

            try:
                ds.tms_y_origin_top = int(json_data.get('y_origin_top'))
            except:
                pass

            ds.tms_epsg_crs_id = json_data['epsg']
            ds.tms_postgis_crs_id = None
            ds.tms_custom_proj = None

        #WMS
        if ds.type.lower() == KNOWN_DRIVERS.WMS.lower():
            ds.wms_url = json_data['url']
            ds.wms_params = json_data['params']
            ds.wms_layers = json_data['layers']
            ds.wms_turn_over = json_data['turn_over']
            ds.format = json_data['format']

        #WFS
        if ds.type.lower() == KNOWN_DRIVERS.WFS.lower():
            ds.wfs_url = json_data['url']
            # ds.wfs_layers = ConfigReaderHelper.try_read_config(parser, 'wfs', 'layers')

        #GEOJSON
        if ds.type.lower() == KNOWN_DRIVERS.GEOJSON.lower():
            ds.geojson_url = json_data['url']

        #internal stuff
        #ds.file_path = ini_file_path
        #ds.icon_path = os.path.join(dir_path, ds.icon) if ds.icon else None

        return ds

    @classmethod
    def write_to_ini(cls, ds_info, ini_file_path):
        _to_utf = lambda x: x.encode('utf-8') if isinstance(x, unicode) else x
        config = FixedConfigParser()

        config.add_section('general')
        config.add_section('ui')
        config.add_section('license')
        config.add_section(ds_info.type.lower())

       # Required
        config.set('general', 'id', ds_info.id)
        config.set('general', 'type', ds_info.type)

        config.set('ui', 'group', ds_info.group)
        config.set('ui', 'alias', ds_info.alias)
        config.set('ui', 'icon', ds_info.icon)

        # Lic & Terms
        config.set('license', 'name', ds_info.lic_name)
        config.set('license', 'link', ds_info.lic_link)
        config.set('license', 'copyright_text', ds_info.copyright_text)
        config.set('license', 'copyright_link', ds_info.copyright_link)
        config.set('license', 'terms_of_use', ds_info.terms_of_use)

        if ds_info.type == KNOWN_DRIVERS.TMS:
            config.set('tms', 'url', ds_info.tms_url)
            config.set('tms', 'zmin', ds_info.tms_zmin)
            config.set('tms', 'zmax', ds_info.tms_zmax)
            config.set('tms', 'y_origin_top', ds_info.tms_y_origin_top)
            if ds_info.tms_epsg_crs_id:
                config.set('tms', 'epsg_crs_id', ds_info.tms_epsg_crs_id)
            if ds_info.tms_postgis_crs_id:
                config.set('tms', 'postgis_crs_id', ds_info.tms_postgis_crs_id)
            if ds_info.tms_custom_proj:
                config.set('tms', 'custom_proj', ds_info.tms_custom_proj)
            config.set('tms', 'custom_tile_ranges', ds_info.tms_custom_tile_ranges)
            config.set('tms', 'custom_tsize1', ds_info.tms_custom_tsize1)
            config.set('tms', 'custom_origin_x', ds_info.tms_custom_origin_x)
            config.set('tms', 'custom_origin_y', ds_info.tms_custom_origin_y)

        if ds_info.type == KNOWN_DRIVERS.WMS:
            config.set('wms', 'url', ds_info.wms_url)
            config.set('wms', 'params', ds_info.wms_params)
            config.set('wms', 'layers', ds_info.wms_layers)
            config.set('wms', 'turn_over', ds_info.wms_turn_over)

        if ds_info.type == KNOWN_DRIVERS.GDAL:
            config.set('gdal', 'source_file', os.path.basename(ds_info.gdal_source_file))

        if ds_info.type == KNOWN_DRIVERS.WFS:
            config.set('wfs', 'url', ds_info.wfs_url)
            # config.set('wfs', 'layers', ds_info.wfs_layers)

        if ds_info.type == KNOWN_DRIVERS.GEOJSON:
            config.set('geojson', 'url', ds_info.geojson_url)


        with codecs.open(ini_file_path, 'w', 'utf-8') as configfile:
            config.write(configfile)
