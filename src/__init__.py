# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapServices
                                 A QGIS plugin
 Collection of internet map services
                             -------------------
        begin                : 2014-11-21
        copyright            : (C) 2014 by NextGIS
        email                : info@nextgis.org
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load MapServices class from file MapServices.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .map_services import MapServices
    return MapServices(iface)
