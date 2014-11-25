# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapServices
                                 A QGIS plugin
 Collection of internet map services
                              -------------------
        begin                : 2014-11-21
        git sha              : $Format:%H$
        copyright            : (C) 2014 by NextGIS
        email                : info@nextgis.org
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


CURR_PATH = os.path.dirname(__file__)
GROUP_PATHS = [
    os.path.join(CURR_PATH, 'groups'),
]

class GroupFactory():

    def __init__(self):
        groups = []
        for gr_path in GROUP_PATHS:
            pass

    def get_group(cls, group_id):
        in_list = lambda search, list_value: search == list_value
