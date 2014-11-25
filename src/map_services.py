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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QToolButton, QMenu
# Initialize Qt resources from file resources.py
#import resources_rc
# Import the code for the dialog

from map_services_settings_dialog import MapServicesSettingsDialog
import os.path
from iniparse import configparser


class MapServices:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        self.translator = QTranslator()

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MapServices_{}.qm'.format(locale))
        self.add_translations(locale_path)
        #TODO Add translations from data_sources
        #TODO Add translations from data_sources_contribute
        #TODO Add translations from groups
        #TODO Add translations from groups_contribute


        # Create the dialog (after translation) and keep reference
        self.dlg = MapServicesSettingsDialog()

        # Declare instance attributes
        self.actions = []


    def add_translations(self, path):
        if os.path.exists(path):
            self.translator.load(path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MapServices', message)


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = self.plugin_dir + '/icon.png'
        self.menu = QMenu(self.tr(u'Map Services'))
        self.menu.setIcon(QIcon(icon_path))

        # temporary
        settings_act = QAction(QIcon(icon_path), self.tr('Settings'), self.iface.mainWindow())
        #settings_act.on("click")
        tmenu = QMenu('OSM')

        self.actions.append(tmenu)
        self.actions.append(settings_act)

        self.menu.addMenu(tmenu)
        self.menu.addAction(settings_act)
        #end temporary

        #menu
        self.iface.webMenu().addMenu(self.menu)

        #toolbar
        toolbutton = QToolButton()
        toolbutton.setPopupMode(QToolButton.InstantPopup)
        toolbutton.setMenu(self.menu)
        toolbutton.setIcon(self.menu.icon())
        toolbutton.setText(self.menu.title())
        toolbutton.setToolTip(self.menu.title())
        self.tb_action = self.iface.webToolBar().addWidget(toolbutton)

    def unload(self):
        # remove menu
        self.iface.webMenu().removeAction(self.menu.menuAction())
        # remove toolbar button
        self.iface.webToolBar().removeAction(self.tb_action)
        # clean vars
        self.menu = None
        self.toolbutton = None
        self.actions = None

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
