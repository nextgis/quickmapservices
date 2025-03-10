# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TileLayer Plugin
                                 A QGIS plugin
 Plugin layer for Tile Maps
                              -------------------
        begin                : 2012-12-16
        copyright            : (C) 2013 by Minoru Akagi
        email                : akaginch@gmail.com
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

# Import the PyQt and QGIS libraries
import math

from qgis.core import QgsRectangle
from qgis.PyQt.QtCore import QRect, Qt
from qgis.PyQt.QtGui import QImage, QPainter

R = 6378137

debug_mode = 0


class TileDefaultSettings(object):
    ZMIN = 0
    ZMAX = 18


def degreesToMercatorMeters(lon, lat):
    # formula: http://en.wikipedia.org/wiki/Mercator_projection#Mathematics_of_the_Mercator_projection
    x = R * lon * math.pi / 180
    y = R * math.log(math.tan((90 + lat) * math.pi / 360))
    return x, y


class BoundingBox(object):
    def __init__(self, xmin, ymin, xmax, ymax):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    def toQgsRectangle(self):
        return QgsRectangle(self.xmin, self.ymin, self.xmax, self.ymax)

    def toString(self, digitsAfterPoint=None):
        if digitsAfterPoint is None:
            return "%f,%f,%f,%f" % (self.xmin, self.ymin, self.xmax, self.ymax)
        return "%.{0}f,%.{0}f,%.{0}f,%.{0}f".format(digitsAfterPoint) % (
            self.xmin,
            self.ymin,
            self.xmax,
            self.ymax,
        )

    @classmethod
    def degreesToMercatorMeters(cls, bbox):
        xmin, ymin = degreesToMercatorMeters(bbox.xmin, bbox.ymin)
        xmax, ymax = degreesToMercatorMeters(bbox.xmax, bbox.ymax)
        return BoundingBox(xmin, ymin, xmax, ymax)

    @classmethod
    def fromString(cls, s):
        a = map(float, s.split(","))
        return BoundingBox(a[0], a[1], a[2], a[3])


class Tile(object):
    def __init__(self, zoom, x, y, data=None):
        self.zoom = zoom
        self.x = x
        self.y = y
        self.data = data


class Tiles(object):
    def __init__(self, zoom, xmin, ymin, xmax, ymax, serviceInfo):
        self.zoom = zoom
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.TILE_SIZE = serviceInfo.TILE_SIZE
        self.tsize1 = serviceInfo.tsize1
        self.yOriginTop = serviceInfo.yOriginTop
        self.serviceInfo = serviceInfo
        self.tiles = {}

    def addTile(self, url, tile):
        self.tiles[url] = tile

    def setImageData(self, url, data):
        if url in self.tiles:
            self.tiles[url].data = data

    def image(self):
        width = (self.xmax - self.xmin + 1) * self.TILE_SIZE
        height = (self.ymax - self.ymin + 1) * self.TILE_SIZE

        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)

        for tile in self.tiles.values():
            if not tile.data:
                continue

            x = tile.x - self.xmin
            y = tile.y - self.ymin
            rect = QRect(
                x * self.TILE_SIZE,
                y * self.TILE_SIZE,
                self.TILE_SIZE,
                self.TILE_SIZE,
            )

            timg = QImage()
            res = timg.loadFromData(tile.data)
            if res:
                p.drawImage(rect, timg)

            if debug_mode:
                p.setPen(Qt.GlobalColor.black)
                p.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                    # "x: %s, y:%s\nz: %s, data: %s" % (x, y, tile.zoom, tile.data.size())
                    "z: %s, data: %s" % (tile.zoom, tile.data.size()),
                )
                if not res:
                    p.setPen(Qt.GlobalColor.darkRed)
                    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Bad tile")

                p.setPen(Qt.GlobalColor.black)
                p.drawRect(rect)

        return image

    def extent(self):
        size = self.tsize1 / 2 ** (self.zoom - 1)
        if self.serviceInfo.tile_ranges is None:
            return QgsRectangle(
                self.xmin * size - self.tsize1,
                self.tsize1 - (self.ymax + 1) * size,
                (self.xmax + 1) * size - self.tsize1,
                self.tsize1 - self.ymin * size,
            )
        else:
            originX = self.serviceInfo.originX
            originY = self.serviceInfo.originY
            return QgsRectangle(
                originX + self.xmin * size,
                originY - (self.ymax + 1) * size,
                originX + (self.xmax + 1) * size,
                originY - self.ymin * size,
            )


class TileServiceInfo(object):
    TILE_SIZE = 256
    # TSIZE1 = 20037508.342789244 # (R * math.pi)

    def __init__(
        self,
        title,
        credit,
        serviceUrl,
        yOriginTop=1,
        zmin=TileDefaultSettings.ZMIN,
        zmax=TileDefaultSettings.ZMAX,
        bbox=None,
        epsg_crs_id=None,
        postgis_crs_id=None,
        custom_proj=None,
        tile_ranges=None,
        tsize1=R * math.pi,
        originX=-R * math.pi,
        originY=R * math.pi,
    ):
        self.title = title
        self.credit = credit
        self.serviceUrl = serviceUrl
        self.yOriginTop = yOriginTop
        self.zmin = max(zmin, 0)
        self.zmax = zmax
        self.bbox = bbox
        self.epsg_crs_id = epsg_crs_id
        self.postgis_crs_id = postgis_crs_id
        self.custom_proj = custom_proj
        self.tsize1 = tsize1
        self.tile_ranges = tile_ranges
        self.originX = originX
        self.originY = originY

    def tileUrl(self, zoom, x, y):
        if not self.yOriginTop:
            y = (2**zoom - 1) - y
        # Added the form to obtain the quadkey and remplace to use.
        # With the following change using the quadkey allowed, take the variable {q} to represent quadkey field.
        # Source and credits of procedure https://github.com/buckheroux/QuadKey/blob/master/quadkey/tile_system.py
        # Adapting code Nelson Ugalde Araya nugaldea@gmail.com
        if "{q}" in self.serviceUrl:
            quadkey = ""
            for i in range(zoom):
                bit = zoom - i
                digit = ord("0")
                mask = 1 << (bit - 1)  # if (bit - 1) > 0 else 1 >> (bit - 1)
                if (x & mask) != 0:
                    digit += 1
                if (y & mask) != 0:
                    digit += 2
                quadkey += chr(digit)
            return self.serviceUrl.replace("{q}", str(quadkey))

        return (
            self.serviceUrl.replace("{z}", str(zoom))
            .replace("{x}", str(x))
            .replace("{y}", str(y))
        )

    def getTileRect(self, zoom, x, y):
        size = self.tsize1 / 2 ** (zoom - 1)
        return QgsRectangle(
            x * size - self.tsize1,
            self.tsize1 - y * size,
            (x + 1) * size - self.tsize1,
            self.tsize1 - (y + 1) * size,
        )

    def degreesToTile(self, zoom, lon, lat):
        x, y = degreesToMercatorMeters(lon, lat)
        size = self.tsize1 / 2 ** (zoom - 1)
        tx = int((x + self.tsize1) / size)
        ty = int((self.tsize1 - y) / size)
        return tx, ty

    def bboxDegreesToTileRange(self, zoom, bbox):
        xmin, ymin = self.degreesToTile(zoom, bbox.xmin, bbox.ymax)
        xmax, ymax = self.degreesToTile(zoom, bbox.xmax, bbox.ymin)
        return BoundingBox(xmin, ymin, xmax, ymax)

    def __str__(self):
        return "%s (%s)" % (self.title, self.serviceUrl)

    def toArrayForTreeView(self):
        extent = ""
        if self.bbox:
            extent = self.bbox.toString(2)
        return [
            self.title,
            self.credit,
            self.serviceUrl,
            "%d-%d" % (self.zmin, self.zmax),
            extent,
            self.yOriginTop,
        ]

    @classmethod
    def createEmptyInfo(cls):
        return TileServiceInfo("", "", "")
