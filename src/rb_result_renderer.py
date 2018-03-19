"""
/***************************************************************************
 RuGeocoder
                                 A QGIS plugin
 Geocode your csv files to shp
                              -------------------
        begin                : 2012-02-20
        copyright            : (C) 2012 by Nikulin Evgeniy
        email                : nikulin.e at gmail
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
from __future__ import print_function

from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsRubberBand
from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem
from qgis.utils import iface

from .compat2qgis import QGisGeometryType, getCanvasDestinationCrs, getQgsCoordinateTransform

class RubberBandResultRenderer():

    def __init__(self):
        self.iface = iface

        self.srs_wgs84 = QgsCoordinateReferenceSystem(4326)
        self.transformation = getQgsCoordinateTransform(self.srs_wgs84, self.srs_wgs84)

        self.rb = QgsRubberBand(self.iface.mapCanvas(), QGisGeometryType.Point)
        self.rb.setColor(QColor('magenta'))
        self.rb.setIconSize(12)

        self.features_rb = QgsRubberBand(self.iface.mapCanvas(), QGisGeometryType.Point)
        magenta_transp = QColor('#3388ff')
        magenta_transp.setAlpha(120)
        self.features_rb.setColor(magenta_transp)
        self.features_rb.setIconSize(12)
        self.features_rb.setWidth(2)

    def show_point(self, point, center=False):
        #check srs
        if self.need_transform():
            point = self.transform_point(point)

        self.rb.addPoint(point)
        if center:
            self.center_to_point(point)

    def clear(self):
        self.rb.reset(QGisGeometryType.Point)

    def need_transform(self):
        return getCanvasDestinationCrs(self.iface).postgisSrid() != 4326

    def transform_point(self, point):
        #dest_srs_id = getCanvasDestinationCrs(self.iface).srsid()
        #self.transformation.setDestCRSID(dest_srs_id)
        self.transformation.setDestinationCrs(getCanvasDestinationCrs(self.iface))
        try:
            return self.transformation.transform(point)
        except:
            print('Error on transform!')  # DEBUG! need message???
            return

    def transform_bbox(self, bbox):
        #dest_srs_id = getCanvasDestinationCrs(self.iface).srsid()
        #self.transformation.setDestCRSID(dest_srs_id)
        self.transformation.setDestinationCrs(getCanvasDestinationCrs(self.iface))
        try:
            return self.transformation.transformBoundingBox(bbox)
        except:
            print('Error on transform!')  # DEBUG! need message???
            return

    def transform_geom(self, geom):
        #dest_srs_id = getCanvasDestinationCrs(self.iface).srsid()
        #self.transformation.setDestCRSID(dest_srs_id)
        self.transformation.setDestinationCrs(getCanvasDestinationCrs(self.iface))
        try:
            geom.transform(self.transformation)
            return geom
        except:
            print('Error on transform!')  # DEBUG! need message???
            return

    def center_to_point(self, point):
        canvas = self.iface.mapCanvas()
        new_extent = QgsRectangle(canvas.extent())
        new_extent.scale(1, point)
        canvas.setExtent(new_extent)
        canvas.refresh()

    def zoom_to_bbox(self, bbox):
        if self.need_transform():
            bbox = self.transform_bbox(bbox)
        self.iface.mapCanvas().setExtent(bbox)
        self.iface.mapCanvas().refresh()


    def show_feature(self, geom):
        if self.need_transform():
            geom = self.transform_geom(geom)
        self.features_rb.setToGeometry(geom, None)

    def clear_feature(self):
        self.features_rb.reset(QGisGeometryType.Point)
