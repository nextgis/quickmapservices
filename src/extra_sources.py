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
from __future__ import absolute_import
import json
import os
import tempfile
from zipfile import ZipFile
import shutil

from qgis.PyQt.QtCore import QUrl, QEventLoop, QFile, QIODevice
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.core import QgsNetworkAccessManager

from .compat import urlopen
from .compat2qgis import getQGisUserDatabaseFilePath
from .plugin_settings import PluginSettings


LOCAL_SETTINGS_PATH = os.path.dirname(getQGisUserDatabaseFilePath())
PLUGIN_SETTINGS_PATH = os.path.join(LOCAL_SETTINGS_PATH, PluginSettings.product_name())

CONTRIBUTE_DIR_PATH = os.path.join(PLUGIN_SETTINGS_PATH, 'Contribute')
USER_DIR_PATH = os.path.join(PLUGIN_SETTINGS_PATH, 'User')

DATA_SOURCES_DIR_NAME = 'data_sources'
GROUPS_DIR_NAME = 'groups'

# CONTRIBUTE_REPO_URL = 'https://api.github.com/repos/nextgis/quickmapservices_contrib'
CONTRIBUTE_ZIP_DIRECT_URL = 'https://github.com/nextgis/quickmapservices_contrib/archive/refs/tags/v.1.19.zip'


class ExtraSources(object):

    __replies = []

    @classmethod
    def check_extra_dirs(cls):
        if not os.path.exists(PLUGIN_SETTINGS_PATH):
            os.mkdir(PLUGIN_SETTINGS_PATH)
        if not os.path.exists(CONTRIBUTE_DIR_PATH):
            os.mkdir(CONTRIBUTE_DIR_PATH)
        if not os.path.exists(USER_DIR_PATH):
            os.mkdir(USER_DIR_PATH)

        for base_folder in (CONTRIBUTE_DIR_PATH, USER_DIR_PATH):
            ds_folder = os.path.join(base_folder, DATA_SOURCES_DIR_NAME)
            if not os.path.exists(ds_folder):
                os.mkdir(ds_folder)
            groups_folder = os.path.join(base_folder, GROUPS_DIR_NAME)
            if not os.path.exists(groups_folder):
                os.mkdir(groups_folder)

    def load_contrib_pack(self):
        self.check_extra_dirs()

        # get info
        # latest_release_info = self._get_latest_release_info()
        # name = latest_release_info['name']
        # zip_url = latest_release_info['zipball_url']

        # create temp dir
        tmp_dir = tempfile.mkdtemp()

        # download zip file
        zip_file_path = os.path.join(tmp_dir, 'contrib.zip')
        # self._download_file(zip_url, zip_file_path)
        self._download_file(CONTRIBUTE_ZIP_DIRECT_URL, zip_file_path)

        # extract zip to tmp dir
        tmp_extract_dir = os.path.join(tmp_dir, 'contrib')
        self._extract_zip(zip_file_path, tmp_extract_dir)

        #first dir - our content
        src_dir_name = os.listdir(tmp_extract_dir)[0]
        src_dir = os.path.join(tmp_extract_dir, src_dir_name)

        # clear dst dir and copy
        shutil.rmtree(CONTRIBUTE_DIR_PATH, ignore_errors=True)
        shutil.copytree(src_dir, CONTRIBUTE_DIR_PATH)

        # remove tmp dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # def _get_releases_info(self):
    #     response = urlopen('%s/%s' % (CONTRIBUTE_REPO_URL, 'releases'))
    #     releases_info = json.loads(response.read().decode('utf-8'))
    #     return releases_info

    # def _get_latest_release_info(self):
    #     url = '%s/%s/%s' % (CONTRIBUTE_REPO_URL, 'releases', 'latest')
    #     reply = self.__sync_request(url)
    #     latest_release_info = json.loads(reply.data().decode("utf-8"))
    #     return latest_release_info

    def _download_file(self, url, out_path):
        reply = self.__sync_request(url)
        local_file = QFile(out_path)
        local_file.open(QIODevice.WriteOnly)
        local_file.write(reply)
        local_file.close()

    def _extract_zip(self, zip_path, out_path):
        zf = ZipFile(zip_path)
        zf.extractall(out_path)

    def __sync_request(self, url):
        _url = QUrl(url)
        _request = QNetworkRequest(_url)
        self.__replies.append(_request)

        QgsNetworkAccessManager.instance().sslErrors.connect(self.__supress_ssl_errors)

        _reply = QgsNetworkAccessManager.instance().get(_request)

        # wait
        loop = QEventLoop()
        _reply.finished.connect(loop.quit)
        loop.exec_()
        _reply.finished.disconnect(loop.quit)
        QgsNetworkAccessManager.instance().sslErrors.disconnect(self.__supress_ssl_errors)
        loop = None

        error = _reply.error()
        if error != QNetworkReply.NoError:
            raise Exception(error)

        result_code = _reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        result = _reply.readAll()
        self.__replies.append(_reply)
        _reply.deleteLater()

        if result_code in [301, 302, 307]:
            redirect_url = _reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            return self.__sync_request(redirect_url)
        else:
            return result

    def __supress_ssl_errors(self, reply, errors):
        reply.ignoreSslErrors()

