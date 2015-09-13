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
import json
import os
import tempfile
import urllib2
from zipfile import ZipFile
from qgis.core import QgsApplication
import shutil
from plugin_settings import PluginSettings

LOCAL_SETTINGS_PATH = os.path.dirname(QgsApplication.qgisUserDbFilePath())
PLUGIN_SETTINGS_PATH = os.path.join(LOCAL_SETTINGS_PATH, PluginSettings.product_name())

CONTRIBUTE_DIR_PATH = os.path.join(PLUGIN_SETTINGS_PATH, 'Contribute')
USER_DIR_PATH = os.path.join(PLUGIN_SETTINGS_PATH, 'User')

DATA_SOURCES_DIR_NAME = 'data_sources'
GROUPS_DIR_NAME = 'groups'

CONTRIBUTE_REPO_URL = 'https://api.github.com/repos/ANAT01/map-list-servers'


class ExtraSources:

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

    @classmethod
    def load_contrib_pack(cls):
        cls.check_extra_dirs()

        # get info
        latest_release_info = cls._get_latest_release_info()
        name = latest_release_info['name']
        zip_url = latest_release_info['assets'][0]['browser_download_url']

        # create temp dir
        tmp_dir = tempfile.mkdtemp()

        # download zip file
        zip_file_path = os.path.join(tmp_dir, 'contrib.zip')
        cls._download_file(zip_url, zip_file_path)

        # extract zip to tmp dir
        tmp_extract_dir = os.path.join(tmp_dir, 'contrib')
        cls._extract_zip(zip_file_path, tmp_extract_dir)

        #first dir - our content
        src_dir_name = os.listdir(tmp_extract_dir)[0]
        src_dir = os.path.join(tmp_extract_dir, src_dir_name)

        # clear dst dir and copy
        shutil.rmtree(CONTRIBUTE_DIR_PATH, ignore_errors=True)
        shutil.copytree(src_dir, CONTRIBUTE_DIR_PATH)

        # remove tmp dir
        shutil.rmtree(tmp_dir, ignore_errors=True)


    @classmethod
    def _get_releases_info(cls):
        response = urllib2.urlopen('%s/%s' % (CONTRIBUTE_REPO_URL, 'releases'))
        releases_info = json.loads(response.read().decode('utf-8'))
        return releases_info

    @classmethod
    def _get_latest_release_info(cls):
        response = urllib2.urlopen('%s/%s/%s' % (CONTRIBUTE_REPO_URL, 'releases', 'latest'))
        latest_release_info = json.loads(response.read().decode('utf-8'))
        return latest_release_info

    @classmethod
    def _download_file(cls, url, out_path):
        response = urllib2.urlopen(url)
        with open(out_path, "wb") as local_file:
            local_file.write(response.read())

    @classmethod
    def _extract_zip(cls, zip_path, out_path):
        zf = ZipFile(zip_path)
        zf.extractall(out_path)

