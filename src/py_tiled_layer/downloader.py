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
import threading
from qgis.PyQt.QtCore import QObject, QTimer, QEventLoop, QDateTime, qDebug, QUrl, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.core import QgsNetworkAccessManager


debug_mode = 0


class Downloader(QObject):

    NOT_FOUND = 0
    NO_ERROR = 0
    TIMEOUT_ERROR = 4
    UNKNOWN_ERROR = -1

    replyFinished = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.queue = []
        self.redirected_urls = {}
        self.requestingUrls = []
        self.replies = []

        self.eventLoop = QEventLoop()
        self.sync = False
        self.fetchedFiles = {}
        self.clearCounts()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fetchTimedOut)

        # network settings
        self.userAgent = "QuickMapServices tile layer (+https://github.com/nextgis/quickmapservices)"
        self.max_connection = 4
        self.default_cache_expiration = 24
        self.errorStatus = Downloader.NO_ERROR

    def clearCounts(self):
        self.fetchSuccesses = 0
        self.fetchErrors = 0
        self.cacheHits = 0

    def fetchTimedOut(self):
        self.log("Downloader.timeOut()")
        self.abort()
        self.errorStatus = Downloader.TIMEOUT_ERROR

    def abort(self):
        # clear queue and abort sent requests
        self.queue = []
        self.timer.stop()
        for reply in self.replies:
            reply.abort()
        self.errorStatus = Downloader.UNKNOWN_ERROR

    def replyFinishedSlot(self):
        reply = self.sender()
        url = reply.request().url().toString()
        self.log("replyFinishedSlot: %s" % url)
        if not url in self.fetchedFiles:
            self.fetchedFiles[url] = None
        self.requestingUrls.remove(url)
        self.replies.remove(reply)
        isFromCache = 0
        httpStatusCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if reply.error() == QNetworkReply.NoError:
            if httpStatusCode == 301:
                new_url = str(reply.rawHeader("Location"))
                self.addToQueue(new_url, url)
            else:
                self.fetchSuccesses += 1
                if reply.attribute(QNetworkRequest.SourceIsFromCacheAttribute):
                    self.cacheHits += 1
                    isFromCache = 1
                elif not reply.hasRawHeader("Cache-Control"):
                    cache = QgsNetworkAccessManager.instance().cache()
                    if cache:
                        metadata = cache.metaData(reply.request().url())
                        # self.log("Expiration date: " + metadata.expirationDate().toString().encode("utf-8"))
                        if metadata.expirationDate().isNull():
                            metadata.setExpirationDate(
                                QDateTime.currentDateTime().addSecs(self.default_cache_expiration * 60 * 60))
                            cache.updateMetaData(metadata)
                            self.log(
                                "Default expiration date has been set: %s (%d h)" % (url, self.default_cache_expiration))

                if reply.isReadable():
                    data = reply.readAll()
                    if self.redirected_urls.has_key(url):
                        url = self.redirected_urls[url]

                    self.fetchedFiles[url] = data
                else:
                    qDebug("http status code: " + str(httpStatusCode))

                # self.emit(SIGNAL('replyFinished(QString, int, int)'), url, reply.error(), isFromCache)
                self.replyFinished.emit(url, reply.error(), isFromCache)
        else:
            if self.sync and httpStatusCode == 404:
                self.fetchedFiles[url] = self.NOT_FOUND
            self.fetchErrors += 1
            if self.errorStatus == self.NO_ERROR:
                self.errorStatus = self.UNKNOWN_ERROR

        reply.deleteLater()

        if debug_mode:
            qDebug("queue: %d, requesting: %d" % (len(self.queue), len(self.requestingUrls)))

        if len(self.queue) + len(self.requestingUrls) == 0:
            # all replies have been received
            if self.sync:
                self.logT("eventLoop.quit()")
                self.eventLoop.quit()
            else:
                self.timer.stop()
        elif len(self.queue) > 0:
            # start fetching the next file
            self.fetchNext()
        self.log("replyFinishedSlot End: %s" % url)

    def fetchNext(self):
        if len(self.queue) == 0:
            return
        url = self.queue.pop(0)
        self.log("fetchNext: %s" % url)

        request = QNetworkRequest(QUrl(url))
        request.setRawHeader("User-Agent", self.userAgent)
        reply = QgsNetworkAccessManager.instance().get(request)
        reply.finished.connect(self.replyFinishedSlot)
        self.requestingUrls.append(url)
        self.replies.append(reply)
        return reply

    def fetchFiles(self, urlList, timeout_ms=0):
        self.log("fetchFiles()")
        self.sync = True
        self.queue = []
        self.redirected_urls = {} 
        self.clearCounts()
        self.errorStatus = Downloader.NO_ERROR
        self.fetchedFiles = {}

        if len(urlList) == 0:
            return self.fetchedFiles

        for url in urlList:
            self.addToQueue(url)

        for i in range(self.max_connection):
            self.fetchNext()

        if timeout_ms > 0:
            self.timer.setInterval(timeout_ms)
            self.timer.start()

        self.logT("eventLoop.exec_(): " + str(self.eventLoop))
        self.eventLoop.exec_()
        self.log("fetchFiles() End: %d" % self.errorStatus)
        if timeout_ms > 0:
            self.timer.stop()
        return self.fetchedFiles

    def addToQueue(self, url, redirected_from=None):
        if url in self.queue:
            return False
        self.queue.append(url)
        if redirected_from is not None:
            self.redirected_urls[url] = redirected_from
        return True

    def queueCount(self):
        return len(self.queue)

    def finishedCount(self):
        return len(self.fetchedFiles)

    def unfinishedCount(self):
        return len(self.queue) + len(self.requestingUrls)

    def log(self, msg):
        if debug_mode:
            qDebug(msg)

    def logT(self, msg):
        if debug_mode:
            qDebug("%s: %s" % (str(threading.current_thread()), msg))

    def fetchFilesAsync(self, urlList, timeout_ms=0):
        self.log("fetchFilesAsync()")
        self.sync = False
        self.queue = []
        self.clearCounts()
        self.errorStatus = Downloader.NO_ERROR
        self.fetchedFiles = {}

        if len(urlList) == 0:
            return self.fetchedFiles

        for url in urlList:
            self.addToQueue(url)

        for i in range(self.max_connection):
            self.fetchNext()

        if timeout_ms > 0:
            self.timer.setInterval(timeout_ms)
            self.timer.start()
