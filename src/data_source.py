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

class DataSource():

    def __init__(self):
        self.id = None
        self.type = None
        self.is_contrib = None
        self.source_file = None

        self.group = None
        self.alias = None
        self.icon = None

        self.lic_name = None
        self.lic_link = None
        self.copyright_text = None
        self.copyright_link = None
        self.terms_of_use = None

        self.action = None
