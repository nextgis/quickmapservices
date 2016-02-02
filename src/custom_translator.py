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
from singleton import Singleton


class CustomTranslator(QTranslator):

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CustomTranslator, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        super(CustomTranslator, self).__init__()
        self.__translates = {}


    def append(self, text, translation):
        if text and translation:
            self.__translates[text] = translation

    def clear_translations(self):
        self.__translates.clear()

    def translate(self, context, text, disambiguation):
        try:
            if isinstance(text, str) and text in self.__translates.keys():
                return self.__translates[text]
        except:
            return ''
