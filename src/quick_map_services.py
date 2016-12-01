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
import os.path
import urlparse
import xml.etree.ElementTree as ET

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt4.QtGui import QAction, QIcon, QToolButton, QMenu, QMessageBox, QDialog
# Initialize Qt resources from file resources.py
#import resources_rc
# Import the code for the dialog
from qgis.core import QgsProject, QgsPluginLayerRegistry
from qgis.gui import QgsMessageBar
import sys
from .extra_sources import ExtraSources
from .locale import Locale
from .plugin_settings import PluginSettings
from .qgis_map_helpers import add_layer_to_map
from .qms_service_toolbox import QmsServiceToolbox

from .settings_dialog import SettingsDialog
from .about_dialog import AboutDialog
from .py_tiled_layer.tilelayer import TileLayer, TileLayerType
from .data_sources_list import DataSourcesList
from .groups_list import GroupsList
from .custom_translator import CustomTranslator


class QuickMapServices(object):
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
        self.plugin_dir = os.path.dirname(__file__).decode(sys.getfilesystemencoding())

        # initialize locale
        self.translator = QTranslator()

        self.locale = Locale.get_locale()
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QuickMapServices_{}.qm'.format(self.locale))
        if os.path.exists(locale_path):
            self.translator.load(locale_path)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.custom_translator = CustomTranslator()
        QCoreApplication.installTranslator(self.custom_translator)

        # Create the dialog (after translation) and keep reference
        self.info_dlg = AboutDialog()

        # Check Contrib and User dirs
        try:
            ExtraSources.check_extra_dirs()
        except:
            error_message = self.tr('Extra dirs for %s can\'t be created: %s %s') % (PluginSettings.product_name(),
                                                                                      sys.exc_type,
                                                                                      sys.exc_value)
            self.iface.messageBar().pushMessage(self.tr('Error'),
                                                error_message,
                                                level=QgsMessageBar.CRITICAL)

        # Declare instance attributes
        self.service_actions = []
        self.service_layers = []  # TODO: id and smart remove
        self._scales_list = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QuickMapServices', message)

    def initGui(self):
        #import pydevd
        #pydevd.settrace('localhost', port=9921, stdoutToServer=True, stderrToServer=True, suspend=False)

        # Register plugin layer type
        self.tileLayerType = TileLayerType(self)
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.tileLayerType)

        # Create menu
        icon_path = self.plugin_dir + '/icons/mActionAddLayer.png'
        self.menu = QMenu(self.tr(u'QuickMapServices'))
        self.menu.setIcon(QIcon(icon_path))
        self.init_server_panel()

        self.build_menu_tree()

        # add to QGIS menu/toolbars
        self.append_menu_buttons()

    def _load_scales_list(self):
        scales_filename = os.path.join(self.plugin_dir, 'scales.xml')
        scales_list = []
        # TODO: remake when fix: http://hub.qgis.org/issues/11915
        # QgsScaleUtils.loadScaleList(scales_filename, scales_list, importer_message)
        xml_root = ET.parse(scales_filename).getroot()
        for scale_el in xml_root.findall('scale'):
            scales_list.append(scale_el.get('value'))
        return scales_list

    @property
    def scales_list(self):
        if not self._scales_list:
            self._scales_list = self._load_scales_list()
        return self._scales_list

    def set_nearest_scale(self):
        #get current scale
        curr_scale = self.iface.mapCanvas().scale()
        #find nearest
        nearest_scale = sys.maxsize
        for scale_str in self.scales_list:
            scale = scale_str.split(':')[1]
            scale_int = int(scale)
            if abs(scale_int-curr_scale) < abs(nearest_scale - curr_scale):
                nearest_scale = scale_int

        #set new scale
        if nearest_scale != sys.maxsize:
            self.iface.mapCanvas().zoomScale(nearest_scale)

    def set_tms_scales(self):
        res = QMessageBox.question(
            self.iface.mainWindow(),
            self.tr('QuickMapServices'),
            self.tr('Set SlippyMap scales for current project? \nThe previous settings will be overwritten!'),
            QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            # set scales
            QgsProject.instance().writeEntry('Scales', '/ScalesList', self.scales_list)
            # activate
            QgsProject.instance().writeEntry('Scales', '/useProjectScales', True)
            # update in main window
            # ???? no way to update: http://hub.qgis.org/issues/11917

    def insert_layer(self):
        action = self.menu.sender()
        ds = action.data()
        add_layer_to_map(ds)

    def unload(self):
        # remove menu/panels
        self.remove_menu_buttons()
        self.remove_server_panel()

        # clean vars
        self.menu = None
        self.toolbutton = None
        self.service_actions = None
        self.ds_list = None
        self.groups_list = None
        self.service_layers = None
        # Unregister plugin layer type
        QgsPluginLayerRegistry.instance().removePluginLayerType(TileLayer.LAYER_TYPE)

    def build_menu_tree(self):
        # Main Menu
        self.menu.clear()

        self.groups_list = GroupsList()
        self.ds_list = DataSourcesList()

        data_sources = self.ds_list.data_sources.values()
        data_sources.sort(key=lambda x: x.alias or x.id)

        ds_hide_list = PluginSettings.get_hide_ds_id_list()

        for ds in data_sources:
            if ds.id in ds_hide_list:
                continue
            ds.action.triggered.connect(self.insert_layer)
            gr_menu = self.groups_list.get_group_menu(ds.group)
            gr_menu.addAction(ds.action)
            if gr_menu not in self.menu.children():
                self.menu.addMenu(gr_menu)

        # Scales, Settings and About actions
        self.menu.addSeparator()
        icon_set_nearest_scale_path = self.plugin_dir + '/icons/mActionSettings.png'  # TODO change icon
        set_nearest_scale_act = QAction(QIcon(icon_set_nearest_scale_path), self.tr('Set proper scale'), self.iface.mainWindow())
        set_nearest_scale_act.triggered.connect(self.set_nearest_scale)
        self.menu.addAction(set_nearest_scale_act)  # TODO: uncomment after fix
        self.service_actions.append(set_nearest_scale_act)

        icon_scales_path = self.plugin_dir + '/icons/mActionSettings.png'  # TODO change icon
        scales_act = QAction(QIcon(icon_scales_path), self.tr('Set SlippyMap scales'), self.iface.mainWindow())
        scales_act.triggered.connect(self.set_tms_scales)
        #self.menu.addAction(scales_act)  # TODO: uncomment after fix
        self.service_actions.append(scales_act)

        icon_settings_path = self.plugin_dir + '/icons/mapservices.png'
        server_panel_act = self.server_toolbox.toggleViewAction()
        server_panel_act.setIcon(QIcon(icon_settings_path))
        server_panel_act.setText(self.tr('Search QMS'))
        self.service_actions.append(server_panel_act)
        self.menu.addAction(server_panel_act)

        icon_settings_path = self.plugin_dir + '/icons/mActionSettings.png'
        settings_act = QAction(QIcon(icon_settings_path), self.tr('Settings'), self.iface.mainWindow())
        self.service_actions.append(settings_act)
        settings_act.triggered.connect(self.show_settings_dialog)
        self.menu.addAction(settings_act)

        icon_about_path = self.plugin_dir + '/icons/mActionAbout.png'
        info_act = QAction(QIcon(icon_about_path), self.tr('About'), self.iface.mainWindow())
        self.service_actions.append(info_act)
        info_act.triggered.connect(self.info_dlg.show)
        self.menu.addAction(info_act)


    def remove_menu_buttons(self):
        """
        Remove menus/buttons from all toolbars and main submenu
        :return:
        None
        """
        # remove menu
        if self.menu:
            self.iface.webMenu().removeAction(self.menu.menuAction())
            self.iface.addLayerMenu().removeAction(self.menu.menuAction())
        # remove toolbar button
        if self.tb_action:
            self.iface.webToolBar().removeAction(self.tb_action)
            self.iface.layerToolBar().removeAction(self.tb_action)

    def append_menu_buttons(self):
        """
        Append menus and buttons to appropriate toolbar
        :return:
        """
        # add to QGIS menu
        if PluginSettings.move_to_layers_menu():
            self.iface.addLayerMenu().addMenu(self.menu)
        else:
            # need workaround for WebMenu
            _temp_act = QAction('temp', self.iface.mainWindow())
            self.iface.addPluginToWebMenu("_tmp", _temp_act)
            self.iface.webMenu().addMenu(self.menu)
            self.iface.removePluginWebMenu("_tmp", _temp_act)

        # add to QGIS toolbar
        toolbutton = QToolButton()
        toolbutton.setPopupMode(QToolButton.InstantPopup)
        toolbutton.setMenu(self.menu)
        toolbutton.setIcon(self.menu.icon())
        toolbutton.setText(self.menu.title())
        toolbutton.setToolTip(self.menu.title())
        if PluginSettings.move_to_layers_menu():
            self.tb_action = self.iface.layerToolBar().addWidget(toolbutton)
        else:
            self.tb_action = self.iface.webToolBar().addWidget(toolbutton)

    def show_settings_dialog(self):
        settings_dlg = SettingsDialog()
        settings_dlg.exec_()
        # apply settings
        # self.remove_menu_buttons()
        self.build_menu_tree()
        # self.append_menu_buttons()

    def init_server_panel(self):
        self.server_toolbox = QmsServiceToolbox(self.iface)
        self.iface.addDockWidget(PluginSettings.server_dock_area(), self.server_toolbox)
        self.server_toolbox.setWindowIcon(QIcon(self.plugin_dir + '/icons/mapservices.png'))
        self.server_toolbox.setVisible(PluginSettings.server_dock_visibility())
        # self.server_toolbox.setFloating(PluginSettings.dock_floating())
        # self.server_toolbox.resize(PluginSettings.dock_size())
        # self.server_toolbox.move(PluginSettings.dock_pos())
        # self.server_toolbox.setWindowIcon(QIcon(path.join(_current_path, 'edit-find-project.png')))

    def remove_server_panel(self):
        mw = self.iface.mainWindow()
        PluginSettings.set_server_dock_area(mw.dockWidgetArea(self.server_toolbox))
        PluginSettings.set_server_dock_visibility(self.server_toolbox.isVisible())
        # PluginSettings.set_dock_floating(self.__quick_tlb.isFloating())
        # PluginSettings.set_dock_pos(self.__quick_tlb.pos())
        # PluginSettings.set_dock_size(self.__quick_tlb.size())
        # PluginSettings.set_dock_geocoder_name(self.__quick_tlb.get_active_geocoder_name())
        self.iface.removeDockWidget(self.server_toolbox)
        del self.server_toolbox

