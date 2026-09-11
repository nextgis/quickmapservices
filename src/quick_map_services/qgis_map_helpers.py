import random
from typing import Optional
from urllib import parse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsDataSourceUri,
    QgsErrorMessage,
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
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)
from quick_map_services.supported_drivers import KNOWN_DRIVERS

try:
    from qgis.core import QgsVectorTileLayer
except ImportError:
    QgsVectorTileLayer = None

service_layers = []


def add_layer_to_map(ds) -> bool:
    """
    Adds a layer to the current QGIS project based on the datasource config.

    Supports TMS, WMS, WFS, GDAL, GeoJSON, and MVT formats. Sets attribution,
    projection, and correct insertion position in the layer tree.

    :param ds: Datasource description with all needed properties
    :type ds: DataSourceInfo
    :return: Whether at least one layer was added to the project.
    :rtype: bool
    """
    layers4add = []

    # === TMS LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.TMS.lower():
        # Use alternative TMS URL if available
        if ds.alt_tms_urls:
            tms_url = ds.alt_tms_urls[
                random.randint(0, len(ds.alt_tms_urls) - 1)  # noqa: S311 # nosec B311
            ]
        else:
            tms_url = ds.tms_url

        service_url = tms_url.replace("=", "%3D").replace("&", "%26")
        if ds.tms_y_origin_top is not None and ds.tms_y_origin_top == False:
            service_url = service_url.replace("{y}", "{-y}")

        # Construct TMS URI for QGIS
        qgis_tms_uri = "type=xyz&zmin={0}&zmax={1}&url={2}".format(
            ds.tms_zmin if ds.tms_zmin is not None else 0,
            ds.tms_zmax if ds.tms_zmax is not None else 18,
            service_url,
        )

        # Create and configure TMS raster layer
        layer = QgsRasterLayer(
            qgis_tms_uri, ds.alias, KNOWN_DRIVERS.WMS.lower()
        )
        set_tile_layer_proj(
            layer,
            ds.tms_epsg_crs_id,
            ds.tms_postgis_crs_id,
            ds.tms_custom_proj,
        )
        layers4add.append(layer)

    # === GDAL LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.GDAL.lower():
        layer = QgsRasterLayer(ds.gdal_source_file, ds.alias)
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
            qgis_wms_uri, ds.alias, KNOWN_DRIVERS.WMS.lower()
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
                qgis_wfs_uri, "%s - %s" % (ds.alias, layer_name), "WFS"
            )
            layers4add.append(layer)

    # === GEOJSON LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.GEOJSON.lower():
        layer = QgsVectorLayer(ds.geojson_url, ds.alias, "ogr")
        layers4add.append(layer)

    # === MVT LAYERS ===
    if ds.type.lower() == KNOWN_DRIVERS.MVT.lower():
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
        uri.setParam("styleUrl", ds.mvt_style_url)
        uri.setParam("url", ds.mvt_url)
        if ds.mvt_url_name:
            uri.setParam("urlName", ds.mvt_url_name)
        uri.setParam(
            "zmin", str(ds.mvt_zmin) if ds.mvt_zmin is not None else "0"
        )
        uri.setParam(
            "zmax", str(ds.mvt_zmax) if ds.mvt_zmax is not None else "14"
        )

        encoded_uri = uri.encodedUri()
        if isinstance(encoded_uri, QByteArray):
            encoded_uri = encoded_uri.data().decode("utf-8")

        layer = QgsVectorTileLayer(encoded_uri, ds.alias)
        layer.loadDefaultStyle()
        layers4add.append(layer)

    # === ADD LAYERS TO PROJECT ===
    added_layers = 0
    for layer in layers4add:
        if not layer.isValid():
            error_message = f"Layer '{ds.alias}' can't be added to the map!"
            layer_error = layer.error()
            if not layer_error.isEmpty():
                logger.error(
                    "Layer '%s' validation failed: %s",
                    ds.alias,
                    layer_error.message(QgsErrorMessage.Format.Text),
                )

            provider = layer.dataProvider()
            if provider is not None:
                provider_error = provider.error()
                if not provider_error.isEmpty():
                    logger.error(
                        "Provider for layer '%s' validation failed: %s",
                        ds.alias,
                        provider_error.message(QgsErrorMessage.Format.Text),
                    )

            QuickMapServicesInterface.instance().notifier.display_message(
                error_message,
                level=Qgis.MessageLevel.Critical,
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
                KNOWN_DRIVERS.MVT.lower(),
            ):
                position = len(
                    toc_root.children()
                )  # Insert to bottom if wms\tms
            else:
                position = 0  # insert to top

            QgsProject.instance().addMapLayer(layer, False)

            toc_root.insertLayer(position, layer)
            added_layers += 1

            # Save link
            service_layers.append(layer)
            # Set OTF CRS Transform for map
            settings = QmsSettings()
            if settings.enable_otf_3857 and (
                (
                    ds.type.lower() == KNOWN_DRIVERS.TMS.lower()
                    and ds.tms_epsg_crs_id == 3857
                )
                or ds.type.lower() == KNOWN_DRIVERS.MVT.lower()
            ):
                crs_3857 = QgsCoordinateReferenceSystem.fromEpsgId(3857)
                iface.mapCanvas().setDestinationCrs(crs_3857)

                qgis_settings = QSettings()
                new_project_crs_behavior = qgis_settings.value(
                    "/app/projections/newProjectCrsBehavior", "", type=str
                )
                if new_project_crs_behavior == "UsePresetCrs":
                    QgsProject.instance().setCrs(crs_3857)

    return added_layers > 0


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
