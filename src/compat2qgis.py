# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QuickMapServices
                                 A QGIS plugin
 Collection of internet map services
                              -------------------
        begin                : 2014-11-21
        git sha              : $Format:%H$
        copyright            : (C) 2014 by NextGIS
        email                : info@nextgis.com
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import sys

from qgis import core
from qgis.PyQt.QtWidgets import QFileDialog


if hasattr(core, "QGis"):
    from qgis.core import QGis
else:
    from qgis.core import Qgis as QGis


if QGis.QGIS_VERSION_INT >= 30000:
    getQGisUserDatabaseFilePath = core.QgsApplication.qgisUserDatabaseFilePath
    
    addMapLayer =  core.QgsProject.instance().addMapLayer
    
    message_log_levels = {
        "Info": QGis.Info,
        "Warning": QGis.Warning,
        "Critical": QGis.Critical,
    }
    message_bar_levels = message_log_levels

    geometry_types = {
        "Point": core.QgsWkbTypes.PointGeometry,
    }

    qgisRegistryInstance = core.QgsApplication.pluginLayerRegistry()

    imageActionShowAllLayers = ":/images/themes/default/mActionShowAllLayers.svg"
    imageActionHideAllLayers = ":images/themes/default/mActionHideAllLayers.svg"
else:
    getQGisUserDatabaseFilePath = core.QgsApplication.qgisUserDbFilePath
    
    addMapLayer =  core.QgsMapLayerRegistry.instance().addMapLayer

    from qgis.gui import QgsMessageBar    
    from qgis.core import QgsMessageLog    
    message_log_levels = {
        "Info": QgsMessageLog.INFO,
        "Warning": QgsMessageLog.WARNING,
        "Critical": QgsMessageLog.CRITICAL,
    }
    message_bar_levels = {
        "Info": QgsMessageBar.INFO,
        "Warning": QgsMessageBar.WARNING,
        "Critical": QgsMessageBar.CRITICAL,
    }

    geometry_types = {
        "Point": QGis.Point,
    }   

    qgisRegistryInstance = core.QgsPluginLayerRegistry.instance()

    imageActionShowAllLayers = ":/images/themes/default/mActionShowAllLayers.png"
    imageActionHideAllLayers = ":images/themes/default/mActionHideAllLayers.png"

QGisMessageLogLevel = type('QGisMessageLogLevel', (), (message_log_levels)) 
QGisMessageBarLevel = type('QGisMessageBarLevel', (), (message_bar_levels)) 
QGisGeometryType = type('QGisGeometryType', (), (geometry_types))


def getCanvasDestinationCrs(iface):
    if QGis.QGIS_VERSION_INT >= 30000:
        return iface.mapCanvas().mapSettings().destinationCrs()
    else:
        return iface.mapCanvas().mapRenderer().destinationCrs()


class QgsCoordinateTransform(core.QgsCoordinateTransform):
    def __init__(self, src_crs, dst_crs):
        super(QgsCoordinateTransform, self).__init__()
        
        self.setSourceCrs(src_crs)
        self.setDestinationCrs(dst_crs)

    def setDestinationCrs(self, dst_crs):
        if QGis.QGIS_VERSION_INT >= 30000:
            super(QgsCoordinateTransform, self).setDestinationCrs(dst_crs)
        else:
            self.setDestCRS(dst_crs)

def getOpenFileName(parent, caption, filedir, search_filter):
    result = QFileDialog.getOpenFileName(
        parent,
        caption,
        filedir,
        search_filter
    )

    if type(result) == tuple:
        return result[0]
    return result

class QgsCoordinateReferenceSystem(core.QgsCoordinateReferenceSystem):

    def __init__(self, id, type):
        if QGis.QGIS_VERSION_INT >= 30000:
            super(QgsCoordinateReferenceSystem, self).__init__(core.QgsCoordinateReferenceSystem.fromEpsgId(id))
        else:
            super(QgsCoordinateReferenceSystem, self).__init__(id, type)

    @staticmethod
    def fromEpsgId(id):
        if QGis.QGIS_VERSION_INT >= 30000:
            return core.QgsCoordinateReferenceSystem.fromEpsgId(id)
        else:
            return core.QgsCoordinateReferenceSystem(id)