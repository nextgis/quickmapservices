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
from qgis.core import QgsRasterLayer, QgsMessageLog, QgsMapLayerRegistry, QgsProject
from qgis.gui import QgsMessageBar

from map_services_settings_dialog import MapServicesSettingsDialog
import os.path
from group_factory import GroupFactory
from data_source_factory import DataSourceFactory
from about_dialog import AboutDialog


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
        self.settings_dlg = MapServicesSettingsDialog()
        self.info_dlg = AboutDialog()

        # Declare instance attributes
        self.service_actions = []



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
        # Main Menu
        icon_path = self.plugin_dir + '/icons/mActionAddLayer.png'
        self.menu = QMenu(self.tr(u'Map Services'))
        self.menu.setIcon(QIcon(icon_path))

        # DataSources Actions
        #import pydevd
        #pydevd.settrace('localhost', port=9921, stdoutToServer=True, stderrToServer=True, suspend=False)

        self.gr_factory = GroupFactory()
        self.ds_factory = DataSourceFactory()

        for ds in self.ds_factory.data_sources.values():
            ds.action.triggered.connect(self.insert_layer)
            gr_menu = self.gr_factory.get_group_menu(ds.group)
            gr_menu.addAction(ds.action)
            if gr_menu not in self.menu.children():
                self.menu.addMenu(gr_menu)

        # Settings and About actions
        icon_settings_path = self.plugin_dir + '/icons/mActionSettings.png'
        settings_act = QAction(QIcon(icon_settings_path), self.tr('Settings'), self.iface.mainWindow())
        self.service_actions.append(settings_act)
        #self.menu.addAction(settings_act)

        icon_about_path = self.plugin_dir + '/icons/mActionAbout.png'
        info_act = QAction(QIcon(icon_about_path), self.tr('About'), self.iface.mainWindow())
        self.service_actions.append(info_act)
        info_act.triggered.connect(self.info_dlg.show)
        self.menu.addAction(info_act)

        # add to QGIS menu
        self.iface.webMenu().addMenu(self.menu)

        # add to QGIS toolbar
        toolbutton = QToolButton()
        toolbutton.setPopupMode(QToolButton.InstantPopup)
        toolbutton.setMenu(self.menu)
        toolbutton.setIcon(self.menu.icon())
        toolbutton.setText(self.menu.title())
        toolbutton.setToolTip(self.menu.title())
        self.tb_action = self.iface.webToolBar().addWidget(toolbutton)

    def insert_layer(self):
        action = self.menu.sender()
        ds = action.data()
        layer = QgsRasterLayer(ds.source_file, ds.alias)
        if not layer.isValid():
            error_message = self.tr('Layer %s can\'t be added to the map!') % ds.alias
            self.iface.messageBar().pushMessage(self.tr('Error'),
                                                error_message,
                                                level=QgsMessageBar.CRITICAL)
            QgsMessageLog.logMessage(error_message, level=QgsMessageLog.CRITICAL)
        else:
            # Set attribs
            layer.setAttribution(ds.copyright_text)
            layer.setAttributionUrl(ds.copyright_link)
            # Insert to bottom
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            toc_root = QgsProject.instance().layerTreeRoot()
            toc_root.insertLayer(len(toc_root.children()), layer)

    def unload(self):
        # remove menu
        self.iface.webMenu().removeAction(self.menu.menuAction())
        # remove toolbar button
        self.iface.webToolBar().removeAction(self.tb_action)
        # clean vars
        self.menu = None
        self.toolbutton = None
        self.service_actions = None
        self.ds_factory = None
        self.gr_factory = None
