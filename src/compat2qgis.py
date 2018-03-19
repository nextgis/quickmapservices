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

if hasattr(core, "QGis"):
    from qgis.core import QGis
else:
    from qgis.core import Qgis as QGis


if QGis.QGIS_VERSION_INT >= 30000:
    getQGisUserDatabaseFilePath = core.QgsApplication.qgisUserDatabaseFilePath
    
    addMapLayer =  core.QgsProject.instance().addMapLayer
    
    message_levels = {
        "Info": QGis.Info,
        "Warning": QGis.Warning,
        "Critical": QGis.Critical,
    }

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
    message_levels = {
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

QGisMessageLevel = type('QGisMessageLevel', (), (message_levels)) 
QGisGeometryType = type('QGisGeometryType', (), (geometry_types))


def getCanvasDestinationCrs(iface):
    if QGis.QGIS_VERSION_INT >= 30000:
        return iface.mapCanvas().mapSettings().destinationCrs()
    else:
        return iface.mapCanvas().mapRenderer().destinationCrs()

def getQgsCoordinateTransform(src_crs, dst_crs):
    if QGis.QGIS_VERSION_INT >= 30000:
        transformation = core.QgsCoordinateTransform()
        transformation.setSourceCrs(src_crs)
        transformation.setDestinationCrs(dst_crs)
        return transformation
    else:
        return core.QgsCoordinateTransform(src_crs, dst_crs)
