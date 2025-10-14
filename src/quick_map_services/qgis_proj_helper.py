from typing import Optional

from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsMapLayer
from qgis.utils import iface

from .plugin_settings import PluginSettings


class ProjectionHelper:
    CRS_3857 = QgsCoordinateReferenceSystem.fromEpsgId(3857)

    @classmethod
    def set_tile_layer_proj(
        cls,
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
        layer.setCrs(cls.CRS_3857)

        try:
            crs = None
            if epsg_crs_id is not None:
                crs = QgsCoordinateReferenceSystem.fromEpsgId(epsg_crs_id)

            elif postgis_crs_id is not None:
                crs = QgsCoordinateReferenceSystem(
                    postgis_crs_id, QgsCoordinateReferenceSystem.PostgisCrsId
                )

            elif custom_proj is not None:
                custom_crs = QgsCoordinateReferenceSystem()
                custom_crs.createFromProj(custom_proj)

                if custom_crs.isValid() and custom_crs.srsid() == 0:
                    custom_crs.saveAsUserCRS(
                        "quickmapservices " + layer.name()
                    )

                crs = custom_crs

            if crs and crs.isValid():
                layer.setCrs(crs)
        except:
            msg = "Custom crs can't be set for layer {0}!".format(layer.name())
            cls.show_bar_message(msg, Qgis.Warning, 4)

    @classmethod
    def show_bar_message(cls, text, level=Qgis.Info, duration=0, title=None):
        if PluginSettings.show_messages_in_bar():
            if title is None:
                title = PluginSettings.product_name()
            iface.messageBar().pushMessage(title, text, level, duration)
