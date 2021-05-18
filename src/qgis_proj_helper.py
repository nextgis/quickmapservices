from qgis.gui import QgsMessageBar
from qgis.utils import iface

from .plugin_settings import PluginSettings
from .compat2qgis import QGisMessageBarLevel, QgsCoordinateReferenceSystem

class ProjectionHelper:
    CRS_3857 = QgsCoordinateReferenceSystem.fromEpsgId(3857)

    @classmethod
    def set_tile_layer_proj(cls, layer, epsg_crs_id, postgis_crs_id, custom_proj):

        # set standard crs for tiled layer
        layer.setCrs(cls.CRS_3857)
        # set standard/custom crs
        try:
            crs = None
            if epsg_crs_id is not None:
                crs = QgsCoordinateReferenceSystem(epsg_crs_id, QgsCoordinateReferenceSystem.EpsgCrsId)
            if postgis_crs_id is not None:
                crs = QgsCoordinateReferenceSystem(postgis_crs_id, QgsCoordinateReferenceSystem.PostgisCrsId)
            if custom_proj is not None:
                # create form proj4 str
                custom_crs = QgsCoordinateReferenceSystem()
                custom_crs.createFromProj4(custom_proj)
                # try to search in db
                searched = custom_crs.findMatchingProj()
                if searched:
                    crs = QgsCoordinateReferenceSystem(searched, QgsCoordinateReferenceSystem.InternalCrsId)
                else:
                    # create custom and use it
                    custom_crs.saveAsUserCRS(u'quickmapservices ' + layer.name())
                    searched = custom_crs.findMatchingProj()
                    if searched:
                        crs = QgsCoordinateReferenceSystem(searched, QgsCoordinateReferenceSystem.InternalCrsId)
                    else:
                        crs = custom_crs

            if crs:
                layer.setCrs(crs)
        except:
            msg = "Custom crs can't be set for layer {0}!".format(layer.name())
            cls.show_bar_message(msg, QGisMessageBarLevel.Warning, 4)

    @classmethod
    def show_bar_message(cls, text, level=QGisMessageBarLevel.Info, duration=0, title=None):
        if PluginSettings.show_messages_in_bar():
            if title is None:
                title = PluginSettings.product_name()
            iface.messageBar().pushMessage(title, text, level, duration)
