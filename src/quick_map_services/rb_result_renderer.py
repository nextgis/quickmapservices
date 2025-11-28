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

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsRubberBand
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

from quick_map_services.core.compat import GeometryType


class RubberBandResultRenderer:
    def __init__(self):
        self.iface = iface

        self.srs_wgs84 = QgsCoordinateReferenceSystem.fromEpsgId(4326)
        self.transform_decorator = QgsCoordinateTransform(
            self.srs_wgs84, self.srs_wgs84, QgsProject.instance()
        )

        self.rb = QgsRubberBand(self.iface.mapCanvas(), GeometryType.Point)
        self.rb.setColor(QColor("magenta"))
        self.rb.setIconSize(12)

        self.features_rb = QgsRubberBand(
            self.iface.mapCanvas(), GeometryType.Point
        )
        magenta_transp = QColor("#3388ff")
        magenta_transp.setAlpha(120)
        self.features_rb.setColor(magenta_transp)
        self.features_rb.setIconSize(12)
        self.features_rb.setWidth(2)

    def show_point(self, point, center=False):
        # check srs
        if self.need_transform():
            point = self.transform_point(point)

        self.rb.addPoint(point)
        if center:
            self.center_to_point(point)

    def clear(self):
        self.rb.reset(GeometryType.Point)

    def need_transform(self):
        return (
            self.iface.mapCanvas().mapSettings().destinationCrs().postgisSrid()
            != 4326
        )

    def transform_point(self, point):
        self.transform_decorator.setDestinationCrs(
            self.iface.mapCanvas().mapSettings().destinationCrs()
        )
        try:
            return self.transform_decorator.transform(point)
        except:
            print("Error on transform!")  # DEBUG! need message???
            return

    def transform_bbox(self, bbox):
        self.transform_decorator.setDestinationCrs(
            self.iface.mapCanvas().mapSettings().destinationCrs()
        )
        try:
            return self.transform_decorator.transformBoundingBox(bbox)
        except:
            print("Error on transform!")  # DEBUG! need message???
            return

    def transform_geom(self, geom):
        self.transform_decorator.setDestinationCrs(
            self.iface.mapCanvas().mapSettings().destinationCrs()
        )
        try:
            geom.transform(self.transform_decorator)
            return geom
        except Exception as e:
            print("Error on transform! %s" % e)  # DEBUG! need message???
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
        self.features_rb.reset(GeometryType.Point)
