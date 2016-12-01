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


class GroupCategory(object):
    BASE = 'base'
    CONTRIB = 'contributed'
    USER = 'user'

    all = [BASE, CONTRIB, USER]


class GroupInfo(object):

    def __init__(self, group_id=None, alias=None, icon=None, file_path=None, menu=None, category=None):
        # general
        self.id = group_id
        # ui
        self.alias = alias
        self.icon = icon

        # internal
        self.file_path = file_path
        self.menu = menu

        self.category = category
