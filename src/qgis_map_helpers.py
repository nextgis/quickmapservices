from __future__ import absolute_import

import ast
import random

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsMessageLog, QgsProject

from qgis.gui import QgsMessageBar
from qgis.utils import iface

from .compat import urlparse
from .compat2qgis import addMapLayer, QGisMessageLogLevel, QGisMessageBarLevel
from .plugin_settings import PluginSettings
from .supported_drivers import KNOWN_DRIVERS
from .py_tiled_layer.tiles import TileServiceInfo, TileDefaultSettings
from .py_tiled_layer.tilelayer import TileLayer
from .qgis_proj_helper import ProjectionHelper
from .qgis_settings import QGISSettings
from .compat2qgis import message_log_levels

service_layers = []

def tr(message):
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    # return QCoreApplication.translate('QuickMapServices', message)
    return message

def add_layer_to_map(ds):
    layers4add = []

    if ds.type.lower() == KNOWN_DRIVERS.TMS.lower():
        if ds.alt_tms_urls:
            tms_url = ds.alt_tms_urls[random.randint(0, len(ds.alt_tms_urls)-1)]
        else:
            tms_url = ds.tms_url

        if PluginSettings.use_native_tms():     # add version check
            service_url = tms_url.replace("=", "%3D").replace("&", "%26")
            if ds.tms_y_origin_top is not None and ds.tms_y_origin_top==False:
                service_url = service_url.replace('{y}', '{-y}')

            qgis_tms_uri = 'type=xyz&zmin={0}&zmax={1}&url={2}'.format(
                ds.tms_zmin or TileDefaultSettings.ZMIN,
                ds.tms_zmax or TileDefaultSettings.ZMAX,
                service_url
            )

            layer = QgsRasterLayer(qgis_tms_uri, tr(ds.alias), KNOWN_DRIVERS.WMS.lower())
            ProjectionHelper.set_tile_layer_proj(layer, ds.tms_epsg_crs_id, ds.tms_postgis_crs_id, ds.tms_custom_proj)
            layers4add.append(layer)
        else:
            service_info = TileServiceInfo(tr(ds.alias), ds.copyright_text, tms_url)
            service_info.zmin = ds.tms_zmin or service_info.zmin
            service_info.zmax = ds.tms_zmax or service_info.zmax
            if ds.tms_y_origin_top is not None:
                service_info.yOriginTop = ds.tms_y_origin_top
            service_info.epsg_crs_id = ds.tms_epsg_crs_id
            service_info.postgis_crs_id = ds.tms_postgis_crs_id
            service_info.custom_proj = ds.tms_custom_proj

            if ds.tms_tile_ranges is not None: # needs try block & checks that keys are integers etc..
                service_info.tile_ranges = ast.literal_eval(ds.tms_tile_ranges)
            if ds.tms_tsize1 is not None:
                service_info.tsize1 = ds.tms_tsize1
            if ds.tms_origin_x is not None:
                service_info.originX = ds.tms_origin_x
            if ds.tms_origin_y is not None:
                service_info.originY = ds.tms_origin_y

            layer = TileLayer(service_info, False)
            layers4add.append(layer)
    if ds.type.lower() == KNOWN_DRIVERS.GDAL.lower():
        layer = QgsRasterLayer(ds.gdal_source_file, tr(ds.alias))
        layers4add.append(layer)
    if ds.type.lower() == KNOWN_DRIVERS.WMS.lower():
        qgis_wms_uri = u''
        if ds.wms_params:
            qgis_wms_uri += ds.wms_params
        if ds.wms_layers:
            layers = ds.wms_layers.split(',')
            if layers:
                if ds.wms_turn_over:
                    layers.reverse()
                qgis_wms_uri += '&layers=' + '&layers='.join(layers) + '&styles=' * len(layers)
        qgis_wms_uri += '&url=' + ds.wms_url + "?" + ds.wms_url_params.replace("=","%3D").replace("&","%26")

        layer = QgsRasterLayer(qgis_wms_uri, tr(ds.alias), KNOWN_DRIVERS.WMS.lower())
        layers4add.append(layer)
    if ds.type.lower() == KNOWN_DRIVERS.WFS.lower():
        qgis_wfs_uri_base = ds.wfs_url

        if ds.wfs_params is not None:
            qgis_wfs_uri_base += ds.wfs_params

        o = urlparse.urlparse(qgis_wfs_uri_base)
        request_attrs = dict(urlparse.parse_qsl(o.query))

        new_request_attrs = {}
        for k, v in request_attrs.items():
            new_request_attrs[k.upper()] = v

        if ds.wfs_epsg is not None:
            new_request_attrs['SRSNAME'] = "EPSG:{0}".format(ds.wfs_epsg)

        layers = []
        if len(ds.wfs_layers) > 0:
            layers.extend(ds.wfs_layers)
        else:
            layers_str = request_attrs.get('TYPENAME', '')
            layers.extend(layers_str.split())

        for layer_name in layers:
            new_request_attrs['TYPENAME'] = layer_name

            url_parts = list(o)
            url_parts[4] = "&".join(
                ["%s=%s" % (k, v) for k, v in new_request_attrs.items()]
            )

            qgis_wfs_uri = urlparse.urlunparse(url_parts)
            layer = QgsVectorLayer(
                qgis_wfs_uri,
                "%s - %s" % (tr(ds.alias), layer_name),
                "WFS")
            layers4add.append(layer)

    if ds.type.lower() == KNOWN_DRIVERS.GEOJSON.lower():
        layer = QgsVectorLayer(
            ds.geojson_url,
            tr(ds.alias),
            "ogr")
        layers4add.append(layer)

    for layer in layers4add:
        if not layer.isValid():
            error_message = tr('Layer %s can\'t be added to the map!') % ds.alias
            iface.messageBar().pushMessage(tr('Error'),
                                           error_message,
                                           level=QGisMessageBarLevel.Critical)
            QgsMessageLog.logMessage(error_message, level=message_log_levels["Critical"])
        else:
            # Set attribs
            layer.setAttribution(ds.copyright_text)
            layer.setAttributionUrl(ds.copyright_link)
            # Insert layer
            toc_root = QgsProject.instance().layerTreeRoot()

            selected_node = iface.layerTreeView().currentNode()
            if selected_node and selected_node.nodeType() == selected_node.NodeGroup:
                toc_root =  selected_node

            if ds.type.lower() in (KNOWN_DRIVERS.WMS.lower(), KNOWN_DRIVERS.TMS.lower()):
                position = len(toc_root.children())  # Insert to bottom if wms\tms
            else:
                position = 0  # insert to top

            addMapLayer(layer, False)
                
            toc_root.insertLayer(position, layer)

            # Save link
            service_layers.append(layer)
            # Set OTF CRS Transform for map
            if PluginSettings.enable_otf_3857() and ds.type.lower() == KNOWN_DRIVERS.TMS.lower() and ds.tms_epsg_crs_id == TileLayer.CRS_ID_3857:
                if hasattr(iface.mapCanvas(), "setCrsTransformEnabled"):
                    # Need for QGIS2. In QGIS3 CRS transformation is always enabled
                    iface.mapCanvas().setCrsTransformEnabled(True)
                iface.mapCanvas().setDestinationCrs(TileLayer.CRS_3857)

                if QGISSettings.get_new_project_crs_behavior() == QGISSettings.NEW_PROJECT_USE_PRESET_CRS:
                    QgsProject.instance().setCrs(TileLayer.CRS_3857)
