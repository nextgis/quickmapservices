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
from qgis.PyQt.QtCore import QTranslator
from .singleton import singleton


@singleton
class CustomTranslator(QTranslator):
    def __init__(self):
        QTranslator.__init__(self)
        self.__translates = {}

    def append(self, text, translation):
        if text and translation:
            self.__translates[text] = translation

    def clear_translations(self):
        self.__translates.clear()

    def translate(self, context, text, disambiguation, n=-1):
        try:
            if (isinstance(text, str) or isinstance(text, unicode)) and text in self.__translates:
                return self.__translates[text]
            return None
        except:
            return None
