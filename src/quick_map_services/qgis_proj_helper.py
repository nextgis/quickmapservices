from typing import Optional

from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsMapLayer
from qgis.utils import iface

from quick_map_services.core.settings import QmsSettings


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
    def show_bar_message(
        cls,
        text: str,
        level: Qgis.MessageLevel = Qgis.Info,
        duration: int = 0,
        title: Optional[str] = None,
    ) -> None:
        """
        Display a message in the QGIS message bar
        if this feature is enabled in the plugin settings.

        :param text: The message text to display.
        :type text: str
        :param level: Message level (e.g., Info, Warning, Critical).
        :type level: Qgis.MessageLevel
        :param duration: Duration of the message display in seconds (0 = persistent).
        :type duration: int
        :param title: Optional title to show in the message bar.
        :type title: Optional[str]
        :return: None
        :rtype: None
        """
        settings = QmsSettings()
        if settings.show_messages_in_bar:
            if title is None:
                title = QmsSettings.PRODUCT
            iface.messageBar().pushMessage(title, text, level, duration)
