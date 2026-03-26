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
from typing import TYPE_CHECKING, Dict, List, Optional

from osgeo import gdal
from qgis.core import Qgis, QgsProject
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QT_VERSION_STR, QObject, QSysInfo, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QMenu,
    QMessageBox,
    QToolButton,
)
from qgis.utils import iface

from quick_map_services.about_dialog import AboutDialog
from quick_map_services.core import utils
from quick_map_services.core.constants import PACKAGE_NAME, PLUGIN_NAME
from quick_map_services.core.logging import logger
from quick_map_services.core.settings import QmsSettings
from quick_map_services.custom_translator import CustomTranslator
from quick_map_services.data_source_info import DataSourceInfo
from quick_map_services.data_sources_list import DataSourcesList
from quick_map_services.groups_list import GroupsList
from quick_map_services.gui.qms_settings_page import QmsSettingsPageFactory
from quick_map_services.notifier.message_bar_notifier import MessageBarNotifier
from quick_map_services.qgis_map_helpers import add_layer_to_map
from quick_map_services.qms_service_toolbox import QmsServiceToolbox
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)

if TYPE_CHECKING:
    from quick_map_services.notifier.notifier_interface import (
        NotifierInterface,
    )

assert isinstance(iface, QgisInterface)


class QuickMapServices(QuickMapServicesInterface):
    """QGIS Plugin Implementation."""

    _notifier: Optional[MessageBarNotifier]

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

        try:
            utils.ensure_user_dirs()
        except Exception as exc:
            logger.exception(
                f"Failed to create extra directories in plugin storage: {exc}"
            )

        try:
            utils.cleanup_obsolete_dirs()
        except Exception as exc:
            logger.exception(
                f"Failed to cleanup obsolete directories from plugin storage: {exc}"
            )

        # Declare instance attributes
        self.service_actions = []
        self.service_layers = []  # TODO: id and smart remove
        self._scales_list = None

        self._notifier = None

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        :rtype: NotifierInterface
        :raises AssertionError: If notifier is not initialized.
        """
        assert self._notifier is not None, "Notifier is not initialized"
        return self._notifier

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
        self._notifier = MessageBarNotifier(self)

        # Create menu
        icon_path = self.plugin_dir + "/icons/mActionAddLayer.svg"
        self.menu = QMenu(self.tr("QuickMapServices"))
        self.menu.setIcon(QIcon(icon_path))
        self.init_server_panel()

        self.build_menu_tree()

        # add to QGIS menu/toolbars
        self.append_menu_buttons()

        self._qms_settings_page_factory = QmsSettingsPageFactory()
        self.iface.registerOptionsWidgetFactory(
            self._qms_settings_page_factory
        )

        QuickMapServicesInterface.instance().settings_changed.connect(
            self.build_menu_tree
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

        if self._qms_settings_page_factory is not None:
            self.iface.unregisterOptionsWidgetFactory(
                self._qms_settings_page_factory
            )
            self._qms_settings_page_factory.deleteLater()
            self._qms_settings_page_factory = None

        if self._notifier is not None:
            self._notifier.deleteLater()
            self._notifier = None

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

        all_groups = utils.collect_groups(self.ds_list.data_sources.values())

        groups = utils.filter_hidden_data_sources(
            all_groups,
            QmsSettings().hidden_datasource_id_list,
        )

        sorted_group_ids = utils.sort_group_ids(
            groups.keys(),
        )

        self._populate_groups_menu(groups, sorted_group_ids)
        self._add_qms_section()
        self._add_plugin_actions()

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

    def _populate_groups_menu(
        self,
        groups: Dict[str, List[DataSourceInfo]],
        sorted_group_ids: List[str],
    ) -> None:
        """
        Populate menu with grouped data sources.

        :param groups: Grouped data sources.
        :param sorted_group_ids: Ordered group ids.

        :return: None
        """
        for group_id in sorted_group_ids:
            group_menu: QMenu = self.groups_list.get_group_menu(group_id)
            group_menu.clear()

            for data_source in utils.sort_data_sources(groups[group_id]):
                action = data_source.action
                if action is None:
                    continue

                action.triggered.connect(self.insert_layer)
                group_menu.addAction(action)

            self.menu.addMenu(group_menu)

    def _add_qms_section(self) -> None:
        """
        Add QMS service section to menu.

        :return: None
        """
        self.menu.addSeparator()

        self.service_actions.append(self.qms_search_action)
        self.menu.addAction(self.qms_search_action)

        if not self.qms_create_service_action:
            icon_path = f"{self.plugin_dir}/icons/mActionCreate.svg"
            self.qms_create_service_action = QAction(
                self.tr("Add to Search"),
                self.iface.mainWindow(),
            )
            self.qms_create_service_action.setIcon(QIcon(icon_path))
            self.qms_create_service_action.triggered.connect(self.openURL)

        self.menu.addAction(self.qms_create_service_action)

    def _add_plugin_actions(self) -> None:
        """
        Add plugin-related actions to the menu.

        :return: None
        """
        self.menu.addSeparator()

        if not self.set_nearest_scale_act:
            icon_path = f"{self.plugin_dir}/icons/mActionSettings.svg"
            self.set_nearest_scale_act = QAction(
                QIcon(icon_path),
                self.tr("Set proper scale"),
                self.iface.mainWindow(),
            )
            self.set_nearest_scale_act.triggered.connect(
                self.set_nearest_scale
            )
            self.service_actions.append(self.set_nearest_scale_act)

        self.menu.addAction(self.set_nearest_scale_act)

        if not self.scales_act:
            icon_path = f"{self.plugin_dir}/icons/mActionSettings.svg"
            self.scales_act = QAction(
                QIcon(icon_path),
                self.tr("Set SlippyMap scales"),
                self.iface.mainWindow(),
            )
            self.scales_act.triggered.connect(self.set_tms_scales)
            self.service_actions.append(self.scales_act)

        if not self.settings_act:
            icon_path = f"{self.plugin_dir}/icons/mActionSettings.svg"
            self.settings_act = QAction(
                QIcon(icon_path),
                self.tr("Settings"),
                self.iface.mainWindow(),
            )
            self.settings_act.triggered.connect(self.show_settings_dialog)
            self.service_actions.append(self.settings_act)

        self.menu.addAction(self.settings_act)

        if not self.info_act:
            icon_path = f"{self.plugin_dir}/icons/mActionAbout.svg"
            self.info_act = QAction(
                QIcon(icon_path),
                self.tr("About QMS"),
                self.iface.mainWindow(),
            )
            self.info_act.triggered.connect(self.info_dlg.show)
            self.service_actions.append(self.info_act)

        self.menu.addAction(self.info_act)

        self._help_action = QAction(
            QIcon(f"{self.plugin_dir}/icons/qms_logo.svg"),
            "QuickMapServices",
        )
        self._help_action.triggered.connect(self.info_dlg.show)

        plugin_help_menu = self.iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self._help_action)
