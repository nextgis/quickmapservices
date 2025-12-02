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
import sys
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Optional

from osgeo import gdal
from qgis.core import Qgis, QgsProject
from qgis.gui import QgisInterface, QgsMessageBar
from qgis.PyQt.QtCore import QT_VERSION_STR, QObject, QSysInfo, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QMenu,
    QMessageBox,
    QToolButton,
)
from qgis.utils import iface

from quick_map_services.core import utils
from quick_map_services.core.constants import PACKAGE_NAME, PLUGIN_NAME
from quick_map_services.core.logging import logger
from quick_map_services.core.settings import QmsSettings
from quick_map_services.gui.qms_settings_page import QmsSettingsPageFactory
from quick_map_services.notifier.message_bar_notifier import MessageBarNotifier
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)

from .about_dialog import AboutDialog
from .custom_translator import CustomTranslator
from .data_sources_list import DataSourcesList
from .extra_sources import ExtraSources
from .groups_list import GroupsList
from .qgis_map_helpers import add_layer_to_map
from .qms_service_toolbox import QmsServiceToolbox

if TYPE_CHECKING:
    from quick_map_services.notifier.notifier_interface import (
        NotifierInterface,
    )

assert isinstance(iface, QgisInterface)


class QuickMapServices(QuickMapServicesInterface):
    """QGIS Plugin Implementation."""

    __notifier: Optional[MessageBarNotifier]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Initialize the plugin instance.

        :param parent: Optional parent QObject.
        :type parent: Optional[QObject]
        """
        super().__init__(parent)
        metadata_file = self.path / "metadata.txt"

        logger.debug("<b>✓ Plugin created</b>")
        logger.debug(f"<b>ⓘ OS:</b> {QSysInfo().prettyProductName()}")
        logger.debug(f"<b>ⓘ Qt version:</b> {QT_VERSION_STR}")
        logger.debug(f"<b>ⓘ QGIS version:</b> {Qgis.version()}")
        logger.debug(f"<b>ⓘ Python version:</b> {sys.version}")
        logger.debug(f"<b>ⓘ GDAL version:</b> {gdal.__version__}")
        logger.debug(f"<b>ⓘ Plugin version:</b> {self.version}")
        logger.debug(
            f"<b>ⓘ Plugin path:</b> {self.path}"
            + (
                f" -> {metadata_file.resolve().parent}"
                if metadata_file.is_symlink()
                else ""
            )
        )

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        self.custom_translator = CustomTranslator()

        # Create the dialog (after translation) and keep reference
        self.info_dlg = AboutDialog(PACKAGE_NAME)

        # Check Contrib and User dirs
        try:
            ExtraSources.check_extra_dirs()
        except Exception:
            logger.exception(
                "Failed to create extra directories for QuickMapServices"
            )

            error_message = self.tr(
                "Extra directories for {} could not be created."
            ).format(PLUGIN_NAME)

            self.iface.messageBar().pushMessage(
                self.tr("Error"),
                error_message,
                level=QgsMessageBar.CRITICAL,
            )

        # Declare instance attributes
        self.service_actions = []
        self.service_layers = []  # TODO: id and smart remove
        self._scales_list = None

        self.__notifier = None

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        :rtype: NotifierInterface
        :raises AssertionError: If notifier is not initialized.
        """
        assert self.__notifier is not None, "Notifier is not initialized"
        return self.__notifier

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return self.custom_translator.translate("QuickMapServices", message)

    def _load(self) -> None:
        """
        Initialize the QuickMapServices plugin GUI.
        """
        self._add_translator(
            self.path / "i18n" / f"{PLUGIN_NAME}_{utils.locale()}.qm",
        )
        self.__notifier = MessageBarNotifier(self)

        # Create menu
        icon_path = self.plugin_dir + "/icons/mActionAddLayer.svg"
        self.menu = QMenu(self.tr("QuickMapServices"))
        self.menu.setIcon(QIcon(icon_path))
        self.init_server_panel()

        self.build_menu_tree()

        # add to QGIS menu/toolbars
        self.append_menu_buttons()

        self.__qms_settings_page_factory = QmsSettingsPageFactory()
        self.iface.registerOptionsWidgetFactory(
            self.__qms_settings_page_factory
        )

    def _load_scales_list(self):
        scales_filename = os.path.join(self.plugin_dir, "scales.xml")
        scales_list = []
        # TODO: remake when fix: http://hub.qgis.org/issues/11915
        # QgsScaleUtils.loadScaleList(scales_filename, scales_list, importer_message)
        xml_root = ET.parse(scales_filename).getroot()
        for scale_el in xml_root.findall("scale"):
            scales_list.append(scale_el.get("value"))
        return scales_list

    @property
    def scales_list(self):
        if not self._scales_list:
            self._scales_list = self._load_scales_list()
        return self._scales_list

    def set_nearest_scale(self):
        # get current scale
        curr_scale = self.iface.mapCanvas().scale()
        # find nearest
        nearest_scale = sys.maxsize
        for scale_str in self.scales_list:
            scale = scale_str.split(":")[1]
            scale_int = int(scale)
            if abs(scale_int - curr_scale) < abs(nearest_scale - curr_scale):
                nearest_scale = scale_int

        # set new scale
        if nearest_scale != sys.maxsize:
            self.iface.mapCanvas().zoomScale(nearest_scale)

    def set_tms_scales(self):
        res = QMessageBox.question(
            self.iface.mainWindow(),
            self.tr("QuickMapServices"),
            self.tr(
                "Set SlippyMap scales for current project?\nThe previous settings will be overwritten!"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            # set scales
            QgsProject.instance().writeEntry(
                "Scales", "/ScalesList", self.scales_list
            )
            # activate
            QgsProject.instance().writeEntry(
                "Scales", "/useProjectScales", True
            )
            # update in main window
            # ???? no way to update: http://hub.qgis.org/issues/11917

    def insert_layer(self):
        action = self.menu.sender()
        ds = action.data()
        add_layer_to_map(ds)

    def _unload(self) -> None:
        """
        Unload the QuickMapServices plugin interface.
        """
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

        if self.__qms_settings_page_factory is not None:
            self.iface.unregisterOptionsWidgetFactory(
                self.__qms_settings_page_factory
            )
            self.__qms_settings_page_factory.deleteLater()
            self.__qms_settings_page_factory = None

        if self.__notifier is not None:
            self.__notifier.deleteLater()
            self.__notifier = None

    qms_create_service_action = None
    set_nearest_scale_act = None
    scales_act = None
    settings_act = None
    info_act = None

    def build_menu_tree(self) -> None:
        """
        Build the QuickMapServices main plugin menu in QGIS.

        :return: None
        """
        self.menu.clear()

        self.groups_list = GroupsList()
        self.ds_list = DataSourcesList()

        settings = QmsSettings()

        data_sources = self.ds_list.data_sources.values()
        data_sources = sorted(data_sources, key=lambda x: x.alias or x.id)

        ds_hide_list = settings.hidden_datasource_id_list

        for ds in data_sources:
            if ds.id in ds_hide_list:
                continue
            ds.action.triggered.connect(self.insert_layer)
            gr_menu = self.groups_list.get_group_menu(ds.group)
            gr_menu.addAction(ds.action)
            if gr_menu not in self.menu.children():
                self.menu.addMenu(gr_menu)

        # QMS web service
        self.menu.addSeparator()

        self.service_actions.append(self.qms_search_action)
        self.menu.addAction(self.qms_search_action)

        if not self.qms_create_service_action:
            icon_create_service_path = (
                self.plugin_dir + "/icons/mActionCreate.svg"
            )
            self.qms_create_service_action = QAction(
                self.tr("Add to Search"), self.iface.mainWindow()
            )
            self.qms_create_service_action.setIcon(
                QIcon(icon_create_service_path)
            )
            self.qms_create_service_action.triggered.connect(self.openURL)
        self.menu.addAction(self.qms_create_service_action)

        # Scales, Settings and About actions
        self.menu.addSeparator()

        if not self.set_nearest_scale_act:
            icon_set_nearest_scale_path = (
                self.plugin_dir + "/icons/mActionSettings.svg"
            )  # TODO change icon
            self.set_nearest_scale_act = QAction(
                QIcon(icon_set_nearest_scale_path),
                self.tr("Set proper scale"),
                self.iface.mainWindow(),
            )
            self.set_nearest_scale_act.triggered.connect(
                self.set_nearest_scale
            )
            self.service_actions.append(self.set_nearest_scale_act)
        self.menu.addAction(
            self.set_nearest_scale_act
        )  # TODO: uncomment after fix

        if not self.scales_act:
            icon_scales_path = (
                self.plugin_dir + "/icons/mActionSettings.svg"
            )  # TODO change icon
            self.scales_act = QAction(
                QIcon(icon_scales_path),
                self.tr("Set SlippyMap scales"),
                self.iface.mainWindow(),
            )
            self.scales_act.triggered.connect(self.set_tms_scales)
            self.service_actions.append(self.scales_act)
        # self.menu.addAction(scales_act)  # TODO: uncomment after fix

        if not self.settings_act:
            icon_settings_path = self.plugin_dir + "/icons/mActionSettings.svg"
            self.settings_act = QAction(
                QIcon(icon_settings_path),
                self.tr("Settings"),
                self.iface.mainWindow(),
            )
            self.service_actions.append(self.settings_act)
            self.settings_act.triggered.connect(self.show_settings_dialog)

        self.menu.addAction(self.settings_act)

        if not self.info_act:
            icon_about_path = self.plugin_dir + "/icons/mActionAbout.svg"
            self.info_act = QAction(
                QIcon(icon_about_path),
                self.tr("About QMS"),
                self.iface.mainWindow(),
            )
            self.service_actions.append(self.info_act)
            self.info_act.triggered.connect(self.info_dlg.show)
        self.menu.addAction(self.info_act)

        self.__help_action = QAction(
            QIcon(self.plugin_dir + "/icons/qms_logo.svg"),
            "QuickMapServices",
        )
        self.__help_action.triggered.connect(self.info_dlg.show)

        plugin_help_menu = self.iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self.__help_action)

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

        if self.qms_search_action:
            self.iface.webToolBar().removeAction(self.qms_search_action)
            self.iface.layerToolBar().removeAction(self.qms_search_action)

    def append_menu_buttons(self):
        """
        Append menus and buttons to appropriate toolbar
        :return:
        """

        # need workaround for WebMenu
        _temp_act = QAction("temp", self.iface.mainWindow())
        self.iface.addPluginToWebMenu("_tmp", _temp_act)
        self.iface.webMenu().addMenu(self.menu)
        self.iface.removePluginWebMenu("_tmp", _temp_act)

        # add to QGIS toolbar
        toolbutton = QToolButton()
        toolbutton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbutton.setMenu(self.menu)
        toolbutton.setIcon(self.menu.icon())
        toolbutton.setText(self.menu.title())
        toolbutton.setToolTip(self.menu.title())
        # self.tb_action = toolbutton.defaultAction()
        # print "self.tb_action: ", self.tb_action

        self.tb_action = self.iface.webToolBar().addWidget(toolbutton)
        self.iface.webToolBar().addAction(self.qms_search_action)

    def show_settings_dialog(self) -> None:
        """
        Opens the plugin settings page in the QGIS Options dialog
        """
        self.iface.showOptionsDialog(self.iface.mainWindow(), PLUGIN_NAME)
        self.build_menu_tree()

    def init_server_panel(self) -> None:
        """
        Initialize the QMS Server panel (dock widget) in QGIS.
        """
        self.server_toolbox = QmsServiceToolbox(self.iface)
        self.iface.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.server_toolbox
        )
        self.server_toolbox.setWindowIcon(
            QIcon(self.plugin_dir + "/icons/mActionSearch.svg")
        )

        # QMS search action
        icon_settings_path = self.plugin_dir + "/icons/mActionSearch.svg"
        self.qms_search_action = self.server_toolbox.toggleViewAction()
        self.qms_search_action.setIcon(QIcon(icon_settings_path))
        self.qms_search_action.setText(self.tr("Search NextGIS QMS"))

    def remove_server_panel(self) -> None:
        """
        Remove the QMS Server panel (dock widget) from QGIS.
        """
        self.iface.removeDockWidget(self.server_toolbox)
        del self.server_toolbox

    def openURL(self) -> None:
        """
        Open the QMS create page in the default web browser.

        :return: None
        """
        settings = QmsSettings()
        QDesktopServices.openUrl(QUrl(f"{settings.endpoint_url}/create"))
