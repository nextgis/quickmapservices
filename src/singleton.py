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
from .compat2qgis import QGis

if QGis.QGIS_VERSION_INT >= 30000:
    from qgis.PyQt.QtCore import QObject as QParentClass
else:
  from qgis.PyQt.QtCore import pyqtWrapperType as QParentClass


def singleton(class_):
  instances = {}

  def getinstance(*args, **kwargs):
    if class_ not in instances:
        instances[class_] = class_(*args, **kwargs)
    return instances[class_]

  return getinstance


class QSingleton(QParentClass):
    def __init__(cls, name, bases, dict):
        super(QSingleton, cls).__init__(cls, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(QSingleton, cls).__call__(*args, **kwargs)
        return cls._instance
