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
from PyQt4.QtCore import QTranslator


class CustomTranslator(QTranslator):

    def __init__(self):
        super(QTranslator, self).__init__()
        self.__translates = {}

    def append(self, text, translation):
        if text and translation:
            self.__translates[text] = translation

    def clear_translations(self):
        self.__translates.clear()

    def translate(self, context, text, disambiguation):
        if isinstance(text, str) and text in self.__translates.keys():
            return self.__translates[text]
        return ''
