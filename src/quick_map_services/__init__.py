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

from qgis.core import Qgis, QgsApplication, QgsRuntimeProfiler
from qgis.PyQt.QtCore import QTimer

from quick_map_services.core.exceptions import QmsReloadAfterUpdateWarning
from quick_map_services.core.settings import QmsSettings
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface


def classFactory(iface: "QgisInterface") -> QuickMapServicesInterface:
    """Create and return an instance of the QuickMapServices plugin.

    :param _iface: QGIS interface instance passed by QGIS at plugin load.
    :type _iface: QgisInterface
    :returns: An instance of QuickMapServicesInterface (plugin or stub).
    :rtype: QuickMapServicesInterface
    """
    settings = QmsSettings()

    try:
        with QgsRuntimeProfiler.profile("Import QuickMapServices"):
            from quick_map_services.quick_map_services import QuickMapServices

        plugin = QuickMapServices(iface)
        settings.did_last_launch_fail = False

    except Exception as error:
        from quick_map_services.quick_map_services_plugin_stub import (
            QuickMapServicesPluginStub,
        )

        if not settings.did_last_launch_fail:
            error_to_show = QmsReloadAfterUpdateWarning()
        else:
            error_to_show = error

        settings.did_last_launch_fail = True

        def show_error():
            message = (
                error_to_show.user_message
                if isinstance(error_to_show, QmsReloadAfterUpdateWarning)
                else QgsApplication.translate(
                    "classFactory",
                    "QuickMapServices failed to load: {}",
                ).format(error_to_show)
            )
            bar = iface.messageBar()
            widget = bar.createMessage("QuickMapServices", message)
            bar.pushWidget(widget, Qgis.MessageLevel.Warning)

        QTimer.singleShot(0, show_error)

        return QuickMapServicesPluginStub()

    return plugin
