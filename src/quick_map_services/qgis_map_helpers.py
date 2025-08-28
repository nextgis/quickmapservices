import ast
import random
from urllib import parse

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtCore import QCoreApplication
from qgis.utils import iface

from .compat import QGIS_3_38
from .plugin_settings import PluginSettings
from .qgis_proj_helper import ProjectionHelper
from .qgis_settings import QGISSettings
from .supported_drivers import KNOWN_DRIVERS

service_layers = []


def tr(message):
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    # return QCoreApplication.translate('QuickMapServices', message)
    return message


def add_layer_to_map(ds):
    """
    Adds a layer to the current QGIS project based on the datasource config.

    Supports TMS, WMS, WFS, GDAL, and GeoJSON formats. Sets attribution,
    projection, and correct insertion position in the layer tree.
    Shows a message if the layer is invalid.

    :param ds: Datasource description with all needed properties
    :type ds: Datasource
    """
    layers4add = []

    # === TMS LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.TMS.lower():
        # Use alternative TMS URL if available
        if ds.alt_tms_urls:
            tms_url = ds.alt_tms_urls[
                random.randint(0, len(ds.alt_tms_urls) - 1)
            ]
        else:
            tms_url = ds.tms_url

        service_url = tms_url.replace("=", "%3D").replace("&", "%26")
        if (
            ds.tms_y_origin_top is not None
            and ds.tms_y_origin_top == False
        ):
            service_url = service_url.replace("{y}", "{-y}")

        # Construct TMS URI for QGIS
        qgis_tms_uri = "type=xyz&zmin={0}&zmax={1}&url={2}".format(
            ds.tms_zmin if ds.tms_zmin is not None else 0,
            ds.tms_zmax if ds.tms_zmax is not None else 18,
            service_url,
        )

        # Create and configure TMS raster layer
        layer = QgsRasterLayer(
            qgis_tms_uri, tr(ds.alias), KNOWN_DRIVERS.WMS.lower()
        )
        ProjectionHelper.set_tile_layer_proj(
            layer,
            ds.tms_epsg_crs_id,
            ds.tms_postgis_crs_id,
            ds.tms_custom_proj,
        )
        layers4add.append(layer)

    # === GDAL LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.GDAL.lower():
        layer = QgsRasterLayer(ds.gdal_source_file, tr(ds.alias))
        layers4add.append(layer)
    
    # === WMS LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.WMS.lower():
        qgis_wms_uri = ""
        if ds.wms_params:
            qgis_wms_uri += ds.wms_params
        if ds.wms_layers:
            layers = ds.wms_layers.split(",")
            if layers:
                if ds.wms_turn_over:
                    layers.reverse()
                qgis_wms_uri += (
                    "&layers="
                    + "&layers=".join(layers)
                    + "&styles=" * len(layers)
                )
        qgis_wms_uri += (
            "&url="
            + ds.wms_url
            + "?"
            + ds.wms_url_params.replace("=", "%3D").replace("&", "%26")
        )

        layer = QgsRasterLayer(
            qgis_wms_uri, tr(ds.alias), KNOWN_DRIVERS.WMS.lower()
        )
        layers4add.append(layer)
    
    # === WFS LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.WFS.lower():
        qgis_wfs_uri_base = ds.wfs_url

        if ds.wfs_params is not None:
            qgis_wfs_uri_base += ds.wfs_params

        o = parse.urlparse(qgis_wfs_uri_base)
        request_attrs = dict(parse.parse_qsl(o.query))

        new_request_attrs = {}
        for k, v in request_attrs.items():
            new_request_attrs[k.upper()] = v

        if ds.wfs_epsg is not None:
            new_request_attrs["SRSNAME"] = "EPSG:{0}".format(ds.wfs_epsg)

        layers = []
        if len(ds.wfs_layers) > 0:
            layers.extend(ds.wfs_layers)
        else:
            layers_str = request_attrs.get("TYPENAME", "")
            layers.extend(layers_str.split())

        for layer_name in layers:
            new_request_attrs["TYPENAME"] = layer_name

            url_parts = list(o)
            url_parts[4] = "&".join(
                ["%s=%s" % (k, v) for k, v in new_request_attrs.items()]
            )

            qgis_wfs_uri = parse.urlunparse(url_parts)
            layer = QgsVectorLayer(
                qgis_wfs_uri, "%s - %s" % (tr(ds.alias), layer_name), "WFS"
            )
            layers4add.append(layer)

    # === GEOJSON LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.GEOJSON.lower():
        layer = QgsVectorLayer(ds.geojson_url, tr(ds.alias), "ogr")
        layers4add.append(layer)

    # === ADD LAYERS TO PROJECT ===
    for layer in layers4add:
        if not layer.isValid():
            error_message = (
                tr("Layer %s can't be added to the map!") % ds.alias
            )
            iface.messageBar().pushMessage(
                tr("Error"), error_message, level=Qgis.Critical
            )
            QgsMessageLog.logMessage(
                error_message, level=Qgis.Critical
            )
        else:
            # Set attribs
            if Qgis.versionInt() >= QGIS_3_38:
                server_properties = layer.serverProperties()
                server_properties.setAttribution(ds.copyright_text)
                server_properties.setAttributionUrl(ds.copyright_link)
            else:
                layer.setAttribution(ds.copyright_text)
                layer.setAttributionUrl(ds.copyright_link)

            # Insert layer
            toc_root = QgsProject.instance().layerTreeRoot()

            selected_node = iface.layerTreeView().currentNode()
            if (
                selected_node
                and selected_node.nodeType() == selected_node.NodeGroup
            ):
                toc_root = selected_node

            if ds.type.lower() in (
                KNOWN_DRIVERS.WMS.lower(),
                KNOWN_DRIVERS.TMS.lower(),
            ):
                position = len(
                    toc_root.children()
                )  # Insert to bottom if wms\tms
            else:
                position = 0  # insert to top

            QgsProject.instance().addMapLayer(layer, False)

            toc_root.insertLayer(position, layer)

            # Save link
            service_layers.append(layer)
            # Set OTF CRS Transform for map
            if (
                PluginSettings.enable_otf_3857()
                and ds.type.lower() == KNOWN_DRIVERS.TMS.lower()
                and ds.tms_epsg_crs_id == 3857
            ):
                iface.mapCanvas().setDestinationCrs(QgsCoordinateReferenceSystem.fromEpsgId(3857))

                if (
                    QGISSettings.get_new_project_crs_behavior()
                    == QGISSettings.NEW_PROJECT_USE_PRESET_CRS
                ):
                    QgsProject.instance().setCrs(QgsCoordinateReferenceSystem.fromEpsgId(3857))
