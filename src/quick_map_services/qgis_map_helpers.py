# NextGIS QuickMapServices
# Copyright (C) 2026  NextGIS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

import random
from typing import Optional
from urllib import parse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsDataSourceUri,
    QgsMapLayer,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QByteArray, QSettings
from qgis.utils import iface

from quick_map_services.core.compat import QGIS_3_38
from quick_map_services.core.exceptions import QmsError
from quick_map_services.core.logging import logger
from quick_map_services.core.settings import QmsSettings
from quick_map_services.data_source_info import DataSourceInfo
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)
from quick_map_services.supported_drivers import KNOWN_DRIVERS

try:
    from qgis.core import QgsVectorTileLayer
except ImportError:
    QgsVectorTileLayer = None

service_layers = []


def add_data_source_to_map(data_source: DataSourceInfo) -> None:
    """Add a local data source to the current QGIS project.

    :param data_source: Local data source selected by the user.
    """
    try:
        add_layer_to_map(data_source)
    except Exception as error:
        logger.exception(
            "An error occurred while adding data source to the map"
        )
        QuickMapServicesInterface.instance().notifier.display_exception(error)


def add_layer_to_map(
    data_source: DataSourceInfo,
    qms_id: Optional[int] = None,
) -> None:
    """Add a layer to the current QGIS project from a data source.

    Supports TMS, WMS, WFS, GDAL, and GeoJSON formats. Sets attribution,
    projection, and correct insertion position in the layer tree.

    :param data_source: Data source configuration.
    :param qms_id: Identifier of the service in the Web-QMS catalog.
    """
    layers4add = []

    # === TMS LAYERS ===
    if data_source.type.lower() == KNOWN_DRIVERS.TMS.lower():
        # Use alternative TMS URL if available
        if data_source.alt_tms_urls:
            tms_url = data_source.alt_tms_urls[
                random.randint(  # noqa: S311 # nosec B311
                    0, len(data_source.alt_tms_urls) - 1
                )
            ]
        else:
            tms_url = data_source.tms_url

        service_url = tms_url.replace("=", "%3D").replace("&", "%26")
        if (
            data_source.tms_y_origin_top is not None
            and data_source.tms_y_origin_top == False
        ):
            service_url = service_url.replace("{y}", "{-y}")

        # Construct TMS URI for QGIS
        qgis_tms_uri = "type=xyz&zmin={0}&zmax={1}&url={2}".format(
            data_source.tms_zmin if data_source.tms_zmin is not None else 0,
            data_source.tms_zmax if data_source.tms_zmax is not None else 18,
            service_url,
        )

        # Create and configure TMS raster layer
        layer = QgsRasterLayer(
            qgis_tms_uri, data_source.alias, KNOWN_DRIVERS.WMS.lower()
        )
        set_tile_layer_proj(
            layer,
            data_source.tms_epsg_crs_id,
            data_source.tms_postgis_crs_id,
            data_source.tms_custom_proj,
        )
        layers4add.append(layer)

    # === GDAL LAYERS ===
    if data_source.type.lower() == KNOWN_DRIVERS.GDAL.lower():
        layer = QgsRasterLayer(data_source.gdal_source_file, data_source.alias)
        layers4add.append(layer)

    # === WMS LAYERS ===
    if data_source.type.lower() == KNOWN_DRIVERS.WMS.lower():
        qgis_wms_uri = ""
        if data_source.wms_params:
            qgis_wms_uri += data_source.wms_params
        if data_source.wms_layers:
            layers = data_source.wms_layers.split(",")
            if layers:
                if data_source.wms_turn_over:
                    layers.reverse()
                qgis_wms_uri += (
                    "&layers="
                    + "&layers=".join(layers)
                    + "&styles=" * len(layers)
                )
        qgis_wms_uri += (
            "&url="
            + data_source.wms_url
            + "?"
            + data_source.wms_url_params.replace("=", "%3D").replace(
                "&", "%26"
            )
        )

        layer = QgsRasterLayer(
            qgis_wms_uri, data_source.alias, KNOWN_DRIVERS.WMS.lower()
        )
        layers4add.append(layer)

    # === WFS LAYERS ===
    if data_source.type.lower() == KNOWN_DRIVERS.WFS.lower():
        qgis_wfs_uri_base = data_source.wfs_url

        if data_source.wfs_params is not None:
            qgis_wfs_uri_base += data_source.wfs_params

        o = parse.urlparse(qgis_wfs_uri_base)
        request_attrs = dict(parse.parse_qsl(o.query))

        new_request_attrs = {}
        for k, v in request_attrs.items():
            new_request_attrs[k.upper()] = v

        if data_source.wfs_epsg is not None:
            new_request_attrs["SRSNAME"] = "EPSG:{0}".format(
                data_source.wfs_epsg
            )

        layers = []
        if len(data_source.wfs_layers) > 0:
            layers.extend(data_source.wfs_layers)
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
                qgis_wfs_uri,
                "%s - %s" % (data_source.alias, layer_name),
                "WFS",
            )
            layers4add.append(layer)

    # === GEOJSON LAYERS ===
    if data_source.type.lower() == KNOWN_DRIVERS.GEOJSON.lower():
        layer = QgsVectorLayer(
            data_source.geojson_url, data_source.alias, "ogr"
        )
        layers4add.append(layer)

    # === MVT LAYERS ===
    if data_source.type.lower() == KNOWN_DRIVERS.MVT.lower():
        if QgsVectorTileLayer is None:
            user_message = QgsApplication.translate(
                "QuickMapServices",
                "Your QGIS version does not support vector tile layers.",
            )
            raise QmsError(
                log_message=(
                    "QGIS does not provide QgsVectorTileLayer in this version"
                ),
                user_message=user_message,
            )

        uri = QgsDataSourceUri()
        uri.setParam("type", "xyz")
        uri.setParam("styleUrl", data_source.mvt_style_url)
        uri.setParam("url", data_source.mvt_url)
        uri.setParam(
            "zmin",
            str(data_source.mvt_zmin)
            if data_source.mvt_zmin is not None
            else "0",
        )
        uri.setParam(
            "zmax",
            str(data_source.mvt_zmax)
            if data_source.mvt_zmax is not None
            else "14",
        )

        encoded_uri = uri.encodedUri()
        if isinstance(encoded_uri, QByteArray):
            encoded_uri = encoded_uri.data().decode("utf-8")

        layer = QgsVectorTileLayer(encoded_uri, data_source.alias)
        layer.loadDefaultStyle()
        layers4add.append(layer)

    # === ADD LAYERS TO PROJECT ===
    for layer in layers4add:
        if not layer.isValid():
            error_message = (
                f"Layer '{data_source.alias}' can't be added to the map!"
            )
            QuickMapServicesInterface.instance().notifier.display_message(
                error_message,
                level=Qgis.MessageLevel.Critical,
            )
        else:
            # Set attribs
            if Qgis.versionInt() >= QGIS_3_38:
                server_properties = layer.serverProperties()
                server_properties.setAttribution(data_source.copyright_text)
                server_properties.setAttributionUrl(data_source.copyright_link)
            else:
                layer.setAttribution(data_source.copyright_text)
                layer.setAttributionUrl(data_source.copyright_link)

            # Insert layer
            toc_root = QgsProject.instance().layerTreeRoot()

            selected_node = iface.layerTreeView().currentNode()
            if (
                selected_node
                and selected_node.nodeType() == selected_node.NodeGroup
            ):
                toc_root = selected_node

            if data_source.type.lower() in (
                KNOWN_DRIVERS.WMS.lower(),
                KNOWN_DRIVERS.TMS.lower(),
                KNOWN_DRIVERS.MVT.lower(),
            ):
                position = len(
                    toc_root.children()
                )  # Insert to bottom if wms\tms
            else:
                position = 0  # insert to top

            if qms_id is not None:
                layer.setCustomProperty("qms_id", qms_id)

            QgsProject.instance().addMapLayer(layer, False)

            toc_root.insertLayer(position, layer)

            # Save link
            service_layers.append(layer)
            # Set OTF CRS Transform for map
            settings = QmsSettings()
            if settings.enable_otf_3857 and (
                (
                    data_source.type.lower() == KNOWN_DRIVERS.TMS.lower()
                    and data_source.tms_epsg_crs_id == 3857
                )
                or data_source.type.lower() == KNOWN_DRIVERS.MVT.lower()
            ):
                crs_3857 = QgsCoordinateReferenceSystem.fromEpsgId(3857)
                iface.mapCanvas().setDestinationCrs(crs_3857)

                qgis_settings = QSettings()
                new_project_crs_behavior = qgis_settings.value(
                    "/app/projections/newProjectCrsBehavior", "", type=str
                )
                if new_project_crs_behavior == "UsePresetCrs":
                    QgsProject.instance().setCrs(crs_3857)


def set_tile_layer_proj(
    layer: QgsMapLayer,
    epsg_crs_id: Optional[int] = None,
    postgis_crs_id: Optional[int] = None,
    custom_proj: Optional[str] = None,
) -> None:
    """
    Set CRS for a tile layer based on provided
    EPSG, PostGIS, or custom PROJ string.

    :param layer: QGIS layer object to configure.
    :type layer: QgsMapLayer
    :param epsg_crs_id: EPSG CRS ID (if available).
    :type epsg_crs_id: Optional[int]
    :param postgis_crs_id: PostGIS CRS ID (if available).
    :type postgis_crs_id: Optional[int]
    :param custom_proj: Custom PROJ string (if defined).
    :type custom_proj: Optional[str]
    """
    crs_3857 = QgsCoordinateReferenceSystem.fromEpsgId(3857)
    layer.setCrs(crs_3857)

    try:
        crs = None
        if epsg_crs_id is not None:
            crs = QgsCoordinateReferenceSystem.fromEpsgId(epsg_crs_id)

        elif postgis_crs_id is not None:
            crs = QgsCoordinateReferenceSystem(
                postgis_crs_id,
                QgsCoordinateReferenceSystem.CrsType.PostgisCrsId,
            )

        elif custom_proj is not None:
            custom_crs = QgsCoordinateReferenceSystem()
            custom_crs.createFromProj(custom_proj)

            if custom_crs.isValid() and custom_crs.srsid() == 0:
                custom_crs.saveAsUserCRS("quickmapservices " + layer.name())

            crs = custom_crs

        if crs and crs.isValid():
            layer.setCrs(crs)
            logger.info(
                f"CRS set for layer '{layer.name()}': "
                f"{crs.authid() or 'custom'}"
            )
        elif crs and not crs.isValid():
            QuickMapServicesInterface.instance().notifier.display_message(
                f"Layer '{layer.name()}' CRS is invalid or could not be applied.",
                level=Qgis.MessageLevel.Warning,
            )
    except Exception as error:
        logger.exception("An error occured while setting layer CRS")
        QuickMapServicesInterface.instance().notifier.display_exception(error)
