import urlparse

from PyQt4.QtCore import QCoreApplication
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsMessageLog, QgsMapLayerRegistry, QgsProject
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from plugin_settings import PluginSettings
from supported_drivers import KNOWN_DRIVERS
from py_tiled_layer.tiles import TileServiceInfo
from py_tiled_layer.tilelayer import TileLayer


def tr(message):
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QCoreApplication.translate('QuickMapServices', message)


def add_layer_to_map(ds):
    layers4add = []

    if ds.type.lower() == KNOWN_DRIVERS.TMS.lower():
        service_info = TileServiceInfo(tr(ds.alias), ds.copyright_text, ds.tms_url)
        service_info.zmin = ds.tms_zmin or service_info.zmin
        service_info.zmax = ds.tms_zmax or service_info.zmax
        if ds.tms_y_origin_top is not None:
            service_info.yOriginTop = ds.tms_y_origin_top
        service_info.epsg_crs_id = ds.tms_epsg_crs_id
        service_info.postgis_crs_id = ds.tms_postgis_crs_id
        service_info.custom_proj = ds.tms_custom_proj
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
        qgis_wms_uri += '&url=' + ds.wms_url
        layer = QgsRasterLayer(qgis_wms_uri, tr(ds.alias), KNOWN_DRIVERS.WMS.lower())
        layers4add.append(layer)
    if ds.type.lower() == KNOWN_DRIVERS.WFS.lower():
        qgis_wfs_uri_base = ds.wfs_url
        o = urlparse.urlparse(qgis_wfs_uri_base)
        request_attrs = dict(urlparse.parse_qsl(o.query))

        layers_str = request_attrs.get('TYPENAME', '')
        layers = layers_str.split(',')
        for layer_name in layers:
            new_request_attrs = request_attrs
            new_request_attrs['TYPENAME'] == layer_name

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
                                           level=QgsMessageBar.CRITICAL)
            QgsMessageLog.logMessage(error_message, level=QgsMessageLog.CRITICAL)
        else:
            # Set attribs
            layer.setAttribution(ds.copyright_text)
            layer.setAttributionUrl(ds.copyright_link)
            # Insert to bottom
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            toc_root = QgsProject.instance().layerTreeRoot()
            toc_root.insertLayer(len(toc_root.children()), layer)
            # Save link
            # !!!! self.service_layers.append(layer)
            # Set OTF CRS Transform for map
            if PluginSettings.enable_otf_3857() and ds.type == KNOWN_DRIVERS.TMS:
                iface.mapCanvas().setCrsTransformEnabled(True)
                iface.mapCanvas().setDestinationCrs(TileLayer.CRS_3857)