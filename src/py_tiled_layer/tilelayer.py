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
from __future__ import absolute_import
# Import the PyQt and QGIS libraries
import os
import threading

from qgis.PyQt.QtCore import QObject, qDebug, Qt, QFile, QRectF, QPointF, QPoint, QTimer, QEventLoop, pyqtSignal

from qgis.PyQt.QtGui import QFont, QColor, QBrush
from qgis.core import QgsPluginLayer, QgsPluginLayerType, QgsImageOperation
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from ..plugin_settings import PluginSettings
from ..qgis_settings import QGISSettings
from ..qgis_proj_helper import ProjectionHelper
from ..compat2qgis import QGisMessageBarLevel, QgsCoordinateReferenceSystem

from .tiles import *
from .downloader import Downloader


try:
    from osgeo import gdal

    hasGdal = True
except:
    hasGdal = False

debug_mode = 0


class LayerDefaultSettings(object):
    TRANSPARENCY = 0
    BLEND_MODE = "SourceOver"
    SMOOTH_RENDER = True
    GRAYSCALE_RENDER = False
    BRIGTNESS = 0
    CONTRAST = 1.0


class TileLayer(QgsPluginLayer):
    CRS_ID_3857 = 3857
    CRS_3857 = QgsCoordinateReferenceSystem.fromEpsgId(CRS_ID_3857)

    LAYER_TYPE = "PyTiledLayer"
    MAX_TILE_COUNT = 256
    CHANGE_SCALE_VALUE = 0.30

    fetchRequest = pyqtSignal(list)
    showMessage = pyqtSignal(str, int)
    showBarMessage = pyqtSignal(str, str, int, int)
    allRepliesFinished = pyqtSignal()

    def __init__(self, layerDef, creditVisibility=1):
        QgsPluginLayer.__init__(self, TileLayer.LAYER_TYPE, layerDef.title)

        self.iface = iface
        self.layerDef = layerDef
        self.creditVisibility = 1 if creditVisibility else 0

        # set custom properties
        self.setCustomProperty("title", layerDef.title)
        self.setCustomProperty("credit", layerDef.credit)  # TODO: need to remove
        self.setCustomProperty("serviceUrl", layerDef.serviceUrl)
        self.setCustomProperty("yOriginTop", layerDef.yOriginTop)
        self.setCustomProperty("zmin", layerDef.zmin)
        self.setCustomProperty("zmax", layerDef.zmax)
        if layerDef.bbox:
            self.setCustomProperty("bbox", layerDef.bbox.toString())
        self.setCustomProperty("creditVisibility", self.creditVisibility)

        # set standard/custom crs
        ProjectionHelper.set_tile_layer_proj(self, layerDef.epsg_crs_id, layerDef.postgis_crs_id, layerDef.custom_proj)

        if layerDef.bbox:
            self.setExtent(BoundingBox.degreesToMercatorMeters(layerDef.bbox).toQgsRectangle())
        else:
            if self.layerDef.tile_ranges is not None:
                zmin = sorted(self.layerDef.tile_ranges.keys())[0]
                tbbox = self.layerDef.tile_ranges[zmin]

                size = self.layerDef.tsize1 / 2**(zmin - 1)
                xmin = self.layerDef.originX + tbbox[0] * size
                xmax = self.layerDef.originX + (tbbox[1] + 1) * size
                ymin = self.layerDef.originY - (tbbox[3] + 1) * size
                ymax = self.layerDef.originY - tbbox[2] * size
            else:
                xmin = -layerDef.tsize1
                ymin = -layerDef.tsize1
                xmax = layerDef.tsize1
                ymax = layerDef.tsize1

            self.setExtent(
                QgsRectangle(
                    xmin,
                    ymin,
                    xmax,
                    ymax,
                )
            )

        self.setValid(True)
        self.tiles = None
        self.useLastZoomForPrint = False
        self.canvasLastZoom = 0
        self.setTransparency(LayerDefaultSettings.TRANSPARENCY)
        self.setBlendModeByName(LayerDefaultSettings.BLEND_MODE)
        self.setSmoothRender(LayerDefaultSettings.SMOOTH_RENDER)
        self.setGrayscaleRender(LayerDefaultSettings.GRAYSCALE_RENDER)
        self.setBrigthness(LayerDefaultSettings.BRIGTNESS)
        self.setContrast(LayerDefaultSettings.CONTRAST)

        # downloader
        self.downloader = Downloader(self)
        self.downloader.userAgent = QGISSettings.get_default_user_agent()
        self.downloader.default_cache_expiration = QGISSettings.get_default_tile_expiry()
        self.downloader.max_connection = PluginSettings.default_tile_layer_conn_count()  #TODO: Move to INI files
        self.downloader.replyFinished.connect(self.networkReplyFinished)
        # QObject.connect(self.downloader, SIGNAL("replyFinished(QString, int, int)"), self.networkReplyFinished)

        #network
        self.downloadTimeout = QGISSettings.get_default_network_timeout()

        # multi-thread rendering
        self.eventLoop = None
        
        self.fetchRequest.connect(self.fetchRequestSlot)
        # QObject.connect(self, SIGNAL("fetchRequest(QStringList)"), self.fetchRequest)
        if self.iface:
            # QObject.connect(self, SIGNAL("showMessage(QString, int)"), self.showStatusMessageSlot)
            # QObject.connect(self, SIGNAL("showBarMessage(QString, QString, int, int)"), self.showBarMessageSlot)
            self.showMessage.connect(self.showStatusMessageSlot)
            self.showBarMessage.connect(self.showBarMessageSlot)

    def setBlendModeByName(self, modeName):
        self.blendModeName = modeName
        blendMode = getattr(QPainter, "CompositionMode_" + modeName, 0)
        self.setBlendMode(blendMode)
        self.setCustomProperty("blendMode", modeName)

    def setTransparency(self, transparency):
        self.transparency = transparency
        self.setCustomProperty("transparency", transparency)

    def setSmoothRender(self, isSmooth):
        self.smoothRender = isSmooth
        self.setCustomProperty("smoothRender", 1 if isSmooth else 0)

    def setCreditVisibility(self, visible):
        self.creditVisibility = visible
        self.setCustomProperty("creditVisibility", 1 if visible else 0)

    def setGrayscaleRender(self, isGrayscale):
        self.grayscaleRender = isGrayscale
        self.setCustomProperty("grayscaleRender", 1 if isGrayscale else 0)

    def setBrigthness(self, brigthness):
        self.brigthness = brigthness
        self.setCustomProperty("brigthness", brigthness)

    def setContrast(self, contrast):
        self.contrast = contrast
        self.setCustomProperty("contrast", contrast)

    def draw(self, renderContext):

        self.renderContext = renderContext
        extent = renderContext.extent()
        if extent.isEmpty() or extent.width() == float("inf"):
            qDebug("Drawing is skipped because map extent is empty or inf.")
            return True

        mapSettings = self.iface.mapCanvas().mapSettings()
        painter = renderContext.painter()
        isDpiEqualToCanvas = painter.device().logicalDpiX() == mapSettings.outputDpi()
        if isDpiEqualToCanvas or not self.useLastZoomForPrint:
            # calculate zoom level
            tile_mpp1 = self.layerDef.tsize1 / self.layerDef.TILE_SIZE # should be attribute, not method call..
            viewport_mpp = extent.width() / painter.viewport().width()
            lg = math.log(float(tile_mpp1) / float(viewport_mpp), 2)
            zoom = int(math.modf(lg)[1]) + 1*(math.modf(lg)[0] > self.CHANGE_SCALE_VALUE) + 1
            zoom = max(0, min(zoom, self.layerDef.zmax))
            # zoom = max(self.layerDef.zmin, zoom)
        else:
            # for print composer output image, use last zoom level of map item on print composer (or map canvas)
            zoom = self.canvasLastZoom

        # zoom limit
        if zoom < self.layerDef.zmin:
            msg = self.tr("Current zoom level ({0}) is smaller than zmin ({1}): {2}").format(zoom,
                                                                                             self.layerDef.zmin,
                                                                                             self.layerDef.title)
            self.emitShowBarMessage(msg, QGisMessageBarLevel.Info, 2)
            return True

        while True:
            # calculate tile range (yOrigin is top)
            size = self.layerDef.tsize1 / 2 ** (zoom - 1)
            if self.layerDef.tile_ranges is None: # should add xOffset & yOffset in first part of conditional
                matrixSize = 2 ** zoom
                ulx = max(0, int((extent.xMinimum() + self.layerDef.tsize1) / size))
                uly = max(0, int((self.layerDef.tsize1 - extent.yMaximum()) / size))
                lrx = min(int((extent.xMaximum() + self.layerDef.tsize1) / size), matrixSize - 1)
                lry = min(int((self.layerDef.tsize1 - extent.yMinimum()) / size), matrixSize - 1)
            else: # for tile_ranges
                xmin, xmax, ymin, ymax = self.layerDef.tile_ranges[zoom]

                ulx = max(int((extent.xMinimum() - self.layerDef.originX)/ size), xmin)
                uly = max(int((self.layerDef.originY - extent.yMaximum())/ size), ymin)
                lrx = min(int((extent.xMaximum() - self.layerDef.originX)/ size), xmax)
                lry = min(int((self.layerDef.originY - extent.yMinimum())/ size), ymax)

            # bounding box limit
            if self.layerDef.bbox:
                trange = self.layerDef.bboxDegreesToTileRange(zoom, self.layerDef.bbox)
                ulx = max(ulx, trange.xmin)
                uly = max(uly, trange.ymin)
                lrx = min(lrx, trange.xmax)
                lry = min(lry, trange.ymax)
                if lrx < ulx or lry < uly:
                    # tile range is out of the bounding box
                    return True

            # tile count limit
            tileCount = (lrx - ulx + 1) * (lry - uly + 1)
            if tileCount > self.MAX_TILE_COUNT:
                # as tile count is over the limit, decrease zoom level
                zoom -= 1

                # if the zoom level is less than the minimum, do not draw
                if zoom < self.layerDef.zmin:
                    msg = self.tr("Tile count is over limit ({0}, max={1})").format(tileCount, self.MAX_TILE_COUNT)
                    self.emitShowBarMessage(msg, QGisMessageBarLevel.Warning, 4)
                    return True
                continue

            # zoom level has been determined
            break

        self.logT("TileLayer.draw: {0} {1} {2} {3} {4}".format(zoom, ulx, uly, lrx, lry))

        # save painter state
        painter.save()

        # set pen and font
        painter.setPen(Qt.black)
        font = QFont(painter.font())
        font.setPointSize(10)
        painter.setFont(font)

        if self.layerDef.serviceUrl[0] == ":":
            painter.setBrush(QBrush(Qt.NoBrush))
            self.drawDebugInfo(renderContext, zoom, ulx, uly, lrx, lry)
        else:
            # create Tiles class object and throw url into it
            tiles = Tiles(zoom, ulx, uly, lrx, lry, self.layerDef)
            urls = []
            cacheHits = 0
            for ty in range(uly, lry + 1):
                for tx in range(ulx, lrx + 1):
                    data = None
                    url = self.layerDef.tileUrl(zoom, tx, ty)
                    if self.tiles and zoom == self.tiles.zoom and url in self.tiles.tiles:
                        data = self.tiles.tiles[url].data
                    tiles.addTile(url, Tile(zoom, tx, ty, data))
                    if data is None:
                        urls.append(url)
                    elif data:  # memory cache exists
                        cacheHits += 1
                        # else:    # tile was not found (Downloader.NOT_FOUND=0)

            self.tiles = tiles
            if len(urls) > 0:
                # fetch tile data
                files = self.fetchFiles(urls)

                for url in files.keys():
                    self.tiles.setImageData(url, files[url])

                if self.iface:
                    cacheHits += self.downloader.cacheHits
                    downloadedCount = self.downloader.fetchSuccesses - self.downloader.cacheHits
                    msg = self.tr("{0} files downloaded. {1} cache hits.").format(downloadedCount, cacheHits)
                    barmsg = None
                    if self.downloader.errorStatus != Downloader.NO_ERROR:
                        if self.downloader.errorStatus == Downloader.TIMEOUT_ERROR:
                            barmsg = self.tr("Download Timeout - {}").format(self.name())
                        else:
                            msg += self.tr(" {} files failed.").format(self.downloader.fetchErrors)
                            if self.downloader.fetchSuccesses == 0:
                                barmsg = self.tr("Failed to download all {0} files. - {1}").format(
                                    self.downloader.fetchErrors, self.name())
                    self.showStatusMessage(msg, 5000)
                    if barmsg:
                        self.emitShowBarMessage(barmsg, QGisMessageBarLevel.Warning, 4)

            # apply layer style
            oldOpacity = painter.opacity()
            painter.setOpacity(0.01 * (100 - self.transparency))
            oldSmoothRenderHint = painter.testRenderHint(QPainter.SmoothPixmapTransform)
            if self.smoothRender:
                painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # draw tiles
            if not renderContext.coordinateTransform():
                # no need to reproject tiles
                self.drawTiles(renderContext, self.tiles)
                # self.drawTilesDirectly(renderContext, self.tiles)
            else:
                # reproject tiles
                self.drawTilesOnTheFly(renderContext, self.tiles)

            # restore layer style
            painter.setOpacity(oldOpacity)
            if self.smoothRender:
                painter.setRenderHint(QPainter.SmoothPixmapTransform, oldSmoothRenderHint)

            # draw credit on the bottom right corner
            if self.creditVisibility and self.layerDef.credit:
                margin, paddingH, paddingV = (3, 4, 3)
                # scale
                scaleX, scaleY = self.getScaleToVisibleExtent(renderContext)
                scale = max(scaleX, scaleY)
                painter.scale(scale, scale)

                visibleSWidth = painter.viewport().width() * scaleX / scale
                visibleSHeight = painter.viewport().height() * scaleY / scale
                rect = QRect(0, 0, visibleSWidth - margin, visibleSHeight - margin)
                textRect = painter.boundingRect(rect, Qt.AlignBottom | Qt.AlignRight, self.layerDef.credit)
                bgRect = QRect(textRect.left() - paddingH, textRect.top() - paddingV, textRect.width() + 2 * paddingH,
                               textRect.height() + 2 * paddingV)
                painter.fillRect(bgRect, QColor(240, 240, 240, 150))  # 197, 234, 243, 150))
                painter.drawText(rect, Qt.AlignBottom | Qt.AlignRight, self.layerDef.credit)

        # restore painter state
        painter.restore()

        if isDpiEqualToCanvas:
            # save zoom level for printing (output with different dpi from map canvas)
            self.canvasLastZoom = zoom
        return True

    def drawTiles(self, renderContext, tiles, sdx=1.0, sdy=1.0):
        # create an image that has the same resolution as the tiles
        image = tiles.image()
        if self.grayscaleRender:
            QgsImageOperation.convertToGrayscale(image)
        if self.brigthness != LayerDefaultSettings.BRIGTNESS or self.contrast != LayerDefaultSettings.CONTRAST:
            QgsImageOperation.adjustBrightnessContrast(image, self.brigthness, self.contrast)

        # tile extent to pixel
        map2pixel = renderContext.mapToPixel()
        extent = tiles.extent()
        topLeft = map2pixel.transform(extent.xMinimum(), extent.yMaximum())
        bottomRight = map2pixel.transform(extent.xMaximum(), extent.yMinimum())
        rect = QRectF(QPointF(topLeft.x() * sdx, topLeft.y() * sdy),
                      QPointF(bottomRight.x() * sdx, bottomRight.y() * sdy))

        # draw the image on the map canvas
        renderContext.painter().drawImage(rect, image)

        self.log("Tiles extent: " + str(extent))
        self.log("Draw into canvas rect: " + str(rect))

    def drawTilesOnTheFly(self, renderContext, tiles, sdx=1.0, sdy=1.0):
        if not hasGdal:
            msg = self.tr("Reprojection requires python-gdal")
            self.emitShowBarMessage(msg, QGisMessageBarLevel.Info, 2)
            return

        transform = renderContext.coordinateTransform()
        if not transform:
            return

        # create an image that has the same resolution as the tiles
        image = tiles.image()
        if self.grayscaleRender:
            QgsImageOperation.convertToGrayscale(image)
        if self.brigthness != LayerDefaultSettings.BRIGTNESS or self.contrast != LayerDefaultSettings.CONTRAST:
            QgsImageOperation.adjustBrightnessContrast(image, self.brigthness, self.contrast)

        # tile extent
        extent = tiles.extent()
        geotransform = [extent.xMinimum(), extent.width() / image.width(), 0, extent.yMaximum(), 0,
                        -extent.height() / image.height()]

        driver = gdal.GetDriverByName("MEM")
        tile_ds = driver.Create("", image.width(), image.height(), 1, gdal.GDT_UInt32)
        tile_ds.SetProjection(str(transform.sourceCrs().toWkt()))
        tile_ds.SetGeoTransform(geotransform)

        # QImage to raster
        ba = image.bits().asstring(image.numBytes())
        tile_ds.GetRasterBand(1).WriteRaster(0, 0, image.width(), image.height(), ba)

        # canvas extent
        m2p = renderContext.mapToPixel()
        viewport = renderContext.painter().viewport()
        width = viewport.width()
        height = viewport.height()
        extent = QgsRectangle(m2p.toMapCoordinatesF(0, 0), m2p.toMapCoordinatesF(width, height))
        geotransform = [extent.xMinimum(), extent.width() / width, 0, extent.yMaximum(), 0, -extent.height() / height]

        canvas_ds = driver.Create("", width, height, 1, gdal.GDT_UInt32)
        canvas_ds.SetProjection(str(transform.destCRS().toWkt()))
        canvas_ds.SetGeoTransform(geotransform)

        # reproject image
        gdal.ReprojectImage(tile_ds, canvas_ds)

        # raster to QImage
        ba = canvas_ds.GetRasterBand(1).ReadRaster(0, 0, width, height)
        reprojected_image = QImage(ba, width, height, QImage.Format_ARGB32_Premultiplied)

        # draw the image on the map canvas
        rect = QRectF(QPointF(0, 0), QPointF(viewport.width() * sdx, viewport.height() * sdy))
        renderContext.painter().drawImage(rect, reprojected_image)

    def drawTilesDirectly(self, renderContext, tiles, sdx=1.0, sdy=1.0):
        p = renderContext.painter()
        for url, tile in tiles.tiles.items():
            self.log("Draw tile: zoom: %d, x:%d, y:%d, data:%s" % (tile.zoom, tile.x, tile.y, str(tile.data)))
            rect = self.getTileRect(renderContext, tile.zoom, tile.x, tile.y, sdx, sdy)
            if tile.data:
                image = QImage()
                image.loadFromData(tile.data)
                p.drawImage(rect, image)

    def drawDebugInfo(self, renderContext, zoom, ulx, uly, lrx, lry):
        painter = renderContext.painter()
        scaleX, scaleY = self.getScaleToVisibleExtent(renderContext)
        painter.scale(scaleX, scaleY)

        if "frame" in self.layerDef.serviceUrl:
            self.drawFrames(renderContext, zoom, ulx, uly, lrx, lry, 1.0 / scaleX, 1.0 / scaleY)
        if "number" in self.layerDef.serviceUrl:
            self.drawNumbers(renderContext, zoom, ulx, uly, lrx, lry, 1.0 / scaleX, 1.0 / scaleY)
        if "info" in self.layerDef.serviceUrl:
            self.drawInfo(renderContext, zoom, ulx, uly, lrx, lry)

    def drawFrame(self, renderContext, zoom, x, y, sdx, sdy):
        rect = self.getTileRect(renderContext, zoom, x, y, sdx, sdy)
        p = renderContext.painter()
        # p.drawRect(rect)   # A slash appears on the top-right tile without Antialiasing render hint.
        pts = [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft(), rect.topLeft()]
        for i in range(4):
            p.drawLine(pts[i], pts[i + 1])

    def drawFrames(self, renderContext, zoom, xmin, ymin, xmax, ymax, sdx, sdy):
        for y in range(ymin, ymax + 1):
            for x in range(xmin, xmax + 1):
                self.drawFrame(renderContext, zoom, x, y, sdx, sdy)

    def drawNumber(self, renderContext, zoom, x, y, sdx, sdy):
        rect = self.getTileRect(renderContext, zoom, x, y, sdx, sdy)
        p = renderContext.painter()
        if not self.layerDef.yOriginTop:
            y = (2 ** zoom - 1) - y
        p.drawText(rect, Qt.AlignCenter, "(%d, %d)\nzoom: %d" % (x, y, zoom));

    def drawNumbers(self, renderContext, zoom, xmin, ymin, xmax, ymax, sdx, sdy):
        for y in range(ymin, ymax + 1):
            for x in range(xmin, xmax + 1):
                self.drawNumber(renderContext, zoom, x, y, sdx, sdy)

    def drawInfo(self, renderContext, zoom, xmin, ymin, xmax, ymax):
        # debug information
        mapSettings = self.iface.mapCanvas().mapSettings()
        lines = []
        lines.append("TileLayer")
        lines.append(" zoom: %d, tile matrix extent: (%d, %d) - (%d, %d), tile count: %d * %d" % (
        zoom, xmin, ymin, xmax, ymax, xmax - xmin, ymax - ymin))
        extent = renderContext.extent()
        lines.append(" map extent (renderContext): %s" % extent.toString())
        lines.append(" map center: %lf, %lf" % (extent.center().x(), extent.center().y() ))
        lines.append(" map size: %f, %f" % (extent.width(), extent.height() ))
        lines.append(" map extent (map canvas): %s" % self.iface.mapCanvas().extent().toString())
        m2p = renderContext.mapToPixel()
        painter = renderContext.painter()
        viewport = painter.viewport()
        mapExtent = QgsRectangle(m2p.toMapCoordinatesF(0, 0),
                                 m2p.toMapCoordinatesF(viewport.width(), viewport.height()))
        lines.append(" map extent (calculated): %s" % mapExtent.toString())
        lines.append(" viewport size (pixel): %d, %d" % (viewport.width(), viewport.height() ))
        lines.append(" window size (pixel): %d, %d" % (painter.window().width(), painter.window().height() ))
        lines.append(
            " outputSize (pixel): %d, %d" % (mapSettings.outputSize().width(), mapSettings.outputSize().height() ))
        device = painter.device()
        lines.append(" deviceSize (pixel): %f, %f" % (device.width(), device.height() ))
        lines.append(" logicalDpi: %f, %f" % (device.logicalDpiX(), device.logicalDpiY()))
        lines.append(" outputDpi: %f" % mapSettings.outputDpi())
        lines.append(" mapToPixel: %s" % m2p.showParameters())
        lines.append(" meters per pixel: %f" % (extent.width() / viewport.width()))
        lines.append(" scaleFactor: %f" % renderContext.scaleFactor())
        lines.append(" rendererScale: %f" % renderContext.rendererScale())
        scaleX, scaleY = self.getScaleToVisibleExtent(renderContext)
        lines.append(" scale: %f, %f" % (scaleX, scaleY))

        # draw information
        textRect = painter.boundingRect(QRect(QPoint(0, 0), viewport.size()), Qt.AlignLeft, "Q")
        for i, line in enumerate(lines):
            painter.drawText(10, (i + 1) * textRect.height(), line)
            self.log(line)

        # diagonal
        painter.drawLine(QPointF(0, 0), QPointF(painter.viewport().width(), painter.viewport().height()))
        painter.drawLine(QPointF(painter.viewport().width(), 0), QPointF(0, painter.viewport().height()))

        # credit label
        margin, paddingH, paddingV = (3, 4, 3)
        credit = "This is credit"
        rect = QRect(0, 0, painter.viewport().width() - margin, painter.viewport().height() - margin)
        textRect = painter.boundingRect(rect, Qt.AlignBottom | Qt.AlignRight, credit)
        bgRect = QRect(textRect.left() - paddingH, textRect.top() - paddingV, textRect.width() + 2 * paddingH,
                       textRect.height() + 2 * paddingV)
        painter.drawRect(bgRect)
        painter.drawText(rect, Qt.AlignBottom | Qt.AlignRight, credit)

    def getScaleToVisibleExtent(self, renderContext):
        mapSettings = self.iface.mapCanvas().mapSettings()
        painter = renderContext.painter()
        if painter.device().logicalDpiX() == mapSettings.outputDpi():
            return 1.0, 1.0  # scale should be 1.0 in rendering on map canvas

        extent = renderContext.extent()
        ct = renderContext.coordinateTransform()
        if ct:
            # FIX ME: want to get original visible extent in project CRS or visible view size in pixels

            # extent = ct.transformBoundingBox(extent)
            #xmax, ymin = extent.xMaximum(), extent.yMinimum()

            pt1 = ct.transform(extent.xMaximum(), extent.yMaximum())
            pt2 = ct.transform(extent.xMaximum(), extent.yMinimum())
            pt3 = ct.transform(extent.xMinimum(), extent.yMinimum())
            xmax, ymin = min(pt1.x(), pt2.x()), max(pt2.y(), pt3.y())
        else:
            xmax, ymin = extent.xMaximum(), extent.yMinimum()

        bottomRight = renderContext.mapToPixel().transform(xmax, ymin)
        viewport = painter.viewport()
        scaleX = bottomRight.x() / viewport.width()
        scaleY = bottomRight.y() / viewport.height()
        return scaleX, scaleY

    def getTileRect(self, renderContext, zoom, x, y, sdx=1.0, sdy=1.0, toInt=True):
        """ get tile pixel rect in the render context """
        r = self.layerDef.getTileRect(zoom, x, y)
        map2pix = renderContext.mapToPixel()
        topLeft = map2pix.transform(r.xMinimum(), r.yMaximum())
        bottomRight = map2pix.transform(r.xMaximum(), r.yMinimum())
        if toInt:
            return QRect(QPoint(round(topLeft.x() * sdx), round(topLeft.y() * sdy)),
                         QPoint(round(bottomRight.x() * sdx), round(bottomRight.y() * sdy)))
        else:
            return QRectF(QPointF(topLeft.x() * sdx, topLeft.y() * sdy),
                          QPointF(bottomRight.x() * sdx, bottomRight.y() * sdy))

    def isProjectCrsWebMercator(self):
        mapSettings = self.iface.mapCanvas().mapSettings()
        return mapSettings.destinationCrs().postgisSrid() == 3857

    def networkReplyFinished(self, url, error, isFromCache):
        if self.iface is None or isFromCache:
            return
        unfinishedCount = self.downloader.unfinishedCount()
        if unfinishedCount == 0:
            # self.emit(SIGNAL("allRepliesFinished()"))
            self.allRepliesFinished.emit()


        downloadedCount = self.downloader.fetchSuccesses - self.downloader.cacheHits
        totalCount = self.downloader.finishedCount() + unfinishedCount
        msg = self.tr("{0} of {1} files downloaded.").format(downloadedCount, totalCount)
        if self.downloader.fetchErrors:
            msg += self.tr(" {} files failed.").format(self.downloader.fetchErrors)
        self.showStatusMessage(msg)

    def readXml(self, node):
        self.readCustomProperties(node)
        self.layerDef.title = self.customProperty("title", "")
        self.layerDef.credit = self.customProperty("credit", "")
        if self.layerDef.credit == "":
            self.layerDef.credit = self.customProperty("providerName", "")  # for compatibility with 0.11
        self.layerDef.serviceUrl = self.customProperty("serviceUrl", "")
        self.layerDef.yOriginTop = int(self.customProperty("yOriginTop", 1))
        self.layerDef.zmin = int(self.customProperty("zmin", TileDefaultSettings.ZMIN))
        self.layerDef.zmax = int(self.customProperty("zmax", TileDefaultSettings.ZMAX))
        bbox = self.customProperty("bbox", None)
        if bbox:
            self.layerDef.bbox = BoundingBox.fromString(bbox)
            self.setExtent(BoundingBox.degreesToMercatorMeters(self.layerDef.bbox).toQgsRectangle())
        # layer style
        self.setTransparency(int(self.customProperty("transparency", LayerDefaultSettings.TRANSPARENCY)))
        self.setBlendModeByName(self.customProperty("blendMode", LayerDefaultSettings.BLEND_MODE))
        self.setSmoothRender(int(self.customProperty("smoothRender", LayerDefaultSettings.SMOOTH_RENDER)))
        self.creditVisibility = int(self.customProperty("creditVisibility", 1))
        self.setGrayscaleRender(int(self.customProperty("grayscaleRender", LayerDefaultSettings.GRAYSCALE_RENDER)))
        self.setBrigthness(int(self.customProperty("brigthness", LayerDefaultSettings.BRIGTNESS)))
        self.setContrast(float(self.customProperty("contrast", LayerDefaultSettings.CONTRAST)))

        return True

    def writeXml(self, node, doc):
        element = node.toElement();
        element.setAttribute("type", "plugin")
        element.setAttribute("name", TileLayer.LAYER_TYPE);
        return True

    def readSymbology(self, node, errorMessage):
        return False

    def writeSymbology(self, node, doc, errorMessage):
        return False

    def metadata(self):
        lines = []
        fmt = u"%s:\t%s"
        lines.append(fmt % (self.tr("Title"), self.layerDef.title))
        lines.append(fmt % (self.tr("Credit"), self.layerDef.credit))
        lines.append(fmt % (self.tr("URL"), self.layerDef.serviceUrl))
        lines.append(fmt % (self.tr("yOrigin"), u"%s (yOriginTop=%d)" % (
        ("Bottom", "Top")[self.layerDef.yOriginTop], self.layerDef.yOriginTop)))
        if self.layerDef.bbox:
            extent = self.layerDef.bbox.toString()
        else:
            extent = self.tr("Not set")
        lines.append(fmt % (self.tr("Zoom range"), "%d - %d" % (self.layerDef.zmin, self.layerDef.zmax)))
        lines.append(fmt % (self.tr("Layer Extent"), extent))
        return "\n".join(lines)

    def log(self, msg):
        if debug_mode:
            qDebug(msg)

    def logT(self, msg):
        if debug_mode:
            qDebug("%s: %s" % (str(threading.current_thread()), msg))

    def dump(self, detail=False, bbox=None):
        pass

    # functions for multi-thread rendering
    def fetchFiles(self, urls):
        self.logT("TileLayer.fetchFiles() starts")
        # create a QEventLoop object that belongs to the current thread (if ver. > 2.1, it is render thread)
        eventLoop = QEventLoop()
        self.logT("Create event loop: " + str(eventLoop))  # DEBUG
        # QObject.connect(self, SIGNAL("allRepliesFinished()"), eventLoop.quit)
        self.allRepliesFinished.connect(eventLoop.quit)

        # create a timer to watch whether rendering is stopped
        watchTimer = QTimer()
        watchTimer.timeout.connect(eventLoop.quit)

        # send a fetch request to the main thread
        # self.emit(SIGNAL("fetchRequest(QStringList)"), urls)
        self.fetchRequest.emit(urls)

        # wait for the fetch to finish
        tick = 0
        interval = 500
        timeoutTick = self.downloadTimeout / interval
        watchTimer.start(interval)
        while tick < timeoutTick:
            # run event loop for 0.5 seconds at maximum
            eventLoop.exec_()

            if debug_mode:
                qDebug("watchTimerTick: %d" % tick)
                qDebug("unfinished downloads: %d" % self.downloader.unfinishedCount())

            if self.downloader.unfinishedCount() == 0 or self.renderContext.renderingStopped():
                break
            tick += 1
        watchTimer.stop()

        if tick == timeoutTick and self.downloader.unfinishedCount() > 0:
            self.log("fetchFiles timeout")
            # self.emitShowBarMessage("fetchFiles timeout", duration=5)   #DEBUG
            self.downloader.abort()
            self.downloader.errorStatus = Downloader.TIMEOUT_ERROR
        files = self.downloader.fetchedFiles

        watchTimer.timeout.disconnect(eventLoop.quit)  #
        # QObject.disconnect(self, SIGNAL("allRepliesFinished()"), eventLoop.quit)
        self.allRepliesFinished.disconnect(eventLoop.quit)

        self.logT("TileLayer.fetchFiles() ends")
        return files

    def fetchRequestSlot(self, urls):
        self.logT("TileLayer.fetchRequestSlot()")
        self.downloader.fetchFilesAsync(urls, self.downloadTimeout)

    def showStatusMessage(self, msg, timeout=0):
        # self.emit(SIGNAL("showMessage(QString, int)"), msg, timeout)
        self.showMessage.emit(msg, timeout)

    def showStatusMessageSlot(self, msg, timeout):
        self.iface.mainWindow().statusBar().showMessage(msg, timeout)

    def emitShowBarMessage(self, text, level=QGisMessageBarLevel.Info, duration=0, title=None):
        if PluginSettings.show_messages_in_bar():
            if title is None:
                title = PluginSettings.product_name()
            # self.emit(SIGNAL("showBarMessage(QString, QString, int, int)"), title, text, level, duration)
            self.showBarMessage.emit(title, text, level, duration)

    def showBarMessageSlot(self, title, text, level, duration):
        self.iface.messageBar().pushMessage(title, text, level, duration)


# def createMapRenderer(self, renderContext):
#    qDebug("createMapRenderer")
#    self.renderer = QgsPluginLayerRenderer(self, renderContext)
#    return self.renderer

class TileLayerType(QgsPluginLayerType):
    def __init__(self, plugin):
        QgsPluginLayerType.__init__(self, TileLayer.LAYER_TYPE)

    def createLayer(self):
        return TileLayer(TileServiceInfo.createEmptyInfo())

    def showLayerProperties(self, layer):
        from .propertiesdialog import PropertiesDialog

        dialog = PropertiesDialog(layer)
        # QObject.connect(dialog, SIGNAL("applyClicked()"), self.applyClicked)
        dialog.applyClicked.connect(self.applyClicked)
        dialog.show()
        accepted = dialog.exec_()
        if accepted:
            self.applyProperties(dialog)
        return True

    def applyClicked(self):
        self.applyProperties(QObject().sender())

    def applyProperties(self, dialog):
        layer = dialog.layer
        layer.setTransparency(dialog.ui.spinBox_Transparency.value())
        layer.setBlendModeByName(dialog.ui.comboBox_BlendingMode.currentText())
        layer.setSmoothRender(dialog.ui.checkBox_SmoothRender.isChecked())
        layer.setCreditVisibility(dialog.ui.checkBox_CreditVisibility.isChecked())
        layer.setGrayscaleRender(dialog.ui.checkBox_Grayscale.isChecked())
        layer.setBrigthness(dialog.ui.spinBox_Brightness.value())
        layer.setContrast(dialog.ui.doubleSpinBox_Contrast.value())
        # layer.emit(SIGNAL("repaintRequested()"))
        layer.repaintRequested.emit()
