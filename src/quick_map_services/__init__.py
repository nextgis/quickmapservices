# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QuickMapServices
                                 A QGIS plugin
 Collection of internet map services
                             -------------------
        begin                : 2014-11-21
        copyright            : (C) 2014 by NextGIS
        email                : info@nextgis.com
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

from typing import TYPE_CHECKING

from qgis.core import QgsRuntimeProfiler

from quick_map_services.core.exceptions import QmsReloadAfterUpdateWarning
from quick_map_services.core.settings import QmsSettings
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface


def classFactory(_iface: "QgisInterface") -> QuickMapServicesInterface:
    """Create and return an instance of the QuickMapServices plugin.

    :param _iface: QGIS interface instance passed by QGIS at plugin load.
    :type _iface: QgisInterface
    :returns: An instance of QuickMapServicesInterface (plugin or stub).
    :rtype: QuickMapServicesInterface
    """
    settings = QmsSettings()

    try:
        with QgsRuntimeProfiler.profile("Import plugin"):
            from quick_map_services.quick_map_services import QuickMapServices

        plugin = QuickMapServices()
        settings.did_last_launch_fail = False

    except Exception as error:
        import copy

        from qgis.PyQt.QtCore import QTimer

        from quick_map_services.quick_map_services_plugin_stub import (
            QuickMapServicesPluginStub,
        )

        error_copy = copy.deepcopy(error)
        exception = error_copy

        if not settings.did_last_launch_fail:
            # Sometimes after an update that changes the plugin structure,
            # the plugin may fail to load. Restarting QGIS helps.
            exception = QmsReloadAfterUpdateWarning()
            exception.__cause__ = error_copy

        settings.did_last_launch_fail = True

        plugin = QuickMapServicesPluginStub()

        def display_exception() -> None:
            plugin.notifier.display_exception(exception)

        QTimer.singleShot(0, display_exception)

    return plugin
