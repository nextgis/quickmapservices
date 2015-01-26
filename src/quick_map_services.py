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
import os.path
import xml.etree.ElementTree as ET

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt4.QtGui import QAction, QIcon, QToolButton, QMenu, QMessageBox
# Initialize Qt resources from file resources.py
#import resources_rc
# Import the code for the dialog
from qgis.core import QgsRasterLayer, QgsMessageLog, QgsMapLayerRegistry, QgsProject, QgsPluginLayerRegistry
from qgis.gui import QgsMessageBar
import sys

from settings_dialog import SettingsDialog
from about_dialog import AboutDialog
from py_tiled_layer.tilelayer import TileLayer, TileLayerType
from py_tiled_layer.tiles import TileServiceInfo
from data_sources_list import DataSourcesList
from ds_groups_list import DsGroupsList
from supported_drivers import KNOWN_DRIVERS


class QuickMapServices:
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
            'QuickMapServices_{}.qm'.format(locale))
        self.add_translations(locale_path)
        #TODO Add translations from data_sources
        #TODO Add translations from data_sources_contribute
        #TODO Add translations from groups
        #TODO Add translations from groups_contribute


        # Create the dialog (after translation) and keep reference
        self.settings_dlg = SettingsDialog()
        self.info_dlg = AboutDialog()

        # Declare instance attributes
        self.service_actions = []
        self.service_layers = []  # TODO: id and smart remove
        self._scales_list = None

        # TileLayer assets
        self.crs3857 = None
        self.downloadTimeout = 30  # TODO: settings
        self.navigationMessagesEnabled = Qt.Checked  # TODO: settings
        self.pluginName = 'QuickMapServices'




    def add_translations(self, path):
        if os.path.exists(path):
            self.translator.load(path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QuickMapServices', message)


    def initGui(self):
        #import pydevd
        #pydevd.settrace('localhost', port=9921, stdoutToServer=True, stderrToServer=True, suspend=False)

        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Main Menu
        icon_path = self.plugin_dir + '/icons/mActionAddLayer.png'
        self.menu = QMenu(self.tr(u'QuickMapServices'))
        self.menu.setIcon(QIcon(icon_path))

        # DataSources Actions

        # Register plugin layer type
        self.tileLayerType = TileLayerType(self)
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.tileLayerType)

        self.groups_list = DsGroupsList()
        self.ds_list = DataSourcesList()

        data_sources = self.ds_list.data_sources.values()
        data_sources.sort(key=lambda x: x.alias or x.id)

        for ds in data_sources:
            ds.action.triggered.connect(self.insert_layer)
            gr_menu = self.groups_list.get_group_menu(ds.group)
            gr_menu.addAction(ds.action)
            if gr_menu not in self.menu.children():
                self.menu.addMenu(gr_menu)

        # Scales, Settings and About actions
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
        self.iface.addPluginToWebMenu("_tmp", info_act)
        self.iface.webMenu().addMenu(self.menu)
        self.iface.removePluginWebMenu("_tmp", info_act)

        # add to QGIS toolbar
        toolbutton = QToolButton()
        toolbutton.setPopupMode(QToolButton.InstantPopup)
        toolbutton.setMenu(self.menu)
        toolbutton.setIcon(self.menu.icon())
        toolbutton.setText(self.menu.title())
        toolbutton.setToolTip(self.menu.title())
        self.tb_action = self.iface.webToolBar().addWidget(toolbutton)


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
        nearest_scale = sys.maxint
        for scale_str in self.scales_list:
            scale = scale_str.split(':')[1]
            scale_int = int(scale)
            if abs(scale_int-curr_scale) < abs(nearest_scale - curr_scale):
                nearest_scale = scale_int

        #set new scale
        if nearest_scale != sys.maxint:
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
        #TODO: need factory!
        action = self.menu.sender()
        ds = action.data()
        if ds.type == KNOWN_DRIVERS.TMS:
            service_info = TileServiceInfo(ds.alias, ds.copyright_text, ds.tms_url)
            service_info.zmin = ds.tms_zmin or service_info.zmin
            service_info.zmax = ds.tms_zmax or service_info.zmax
            layer = TileLayer(self, service_info, False)
        if ds.type == KNOWN_DRIVERS.GDAL:
            layer = QgsRasterLayer(ds.gdal_source_file, ds.alias)
        if ds.type == KNOWN_DRIVERS.WMS:
            qgis_wms_uri = u''
            if ds.wms_params:
                qgis_wms_uri += ds.wms_params
            if ds.wms_layers:
                layers = ds.wms_layers.split(',')
                if layers:
                    qgis_wms_uri += '&layers='+'&layers='.join(layers)+'&styles='*len(layers)
            qgis_wms_uri += '&url=' + ds.wms_url
            layer = QgsRasterLayer(qgis_wms_uri, ds.alias, KNOWN_DRIVERS.WMS.lower())

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
            # Save link
            self.service_layers.append(layer)


    def unload(self):
        # remove menu
        self.iface.webMenu().removeAction(self.menu.menuAction())
        # remove toolbar button
        self.iface.webToolBar().removeAction(self.tb_action)
        # clean vars
        self.menu = None
        self.toolbutton = None
        self.service_actions = None
        self.ds_list = None
        self.groups_list = None
        self.service_layers = None
        # Unregister plugin layer type
        QgsPluginLayerRegistry.instance().removePluginLayerType(TileLayer.LAYER_TYPE)
