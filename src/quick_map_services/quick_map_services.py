# NextGIS QuickMapServices
# Copyright (C) 2026  NextGIS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

import os.path
import sys
import xml.etree.ElementTree as ET  # nosec B405
from typing import TYPE_CHECKING, Iterable, Optional

from osgeo import gdal
from qgis.core import Qgis
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QT_VERSION_STR,
    QCoreApplication,
    QObject,
    QSysInfo,
    Qt,
    QUrl,
)
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
from quick_map_services.data_source_info import DataSourceCategory
from quick_map_services.data_sources_catalog import (
    DataSourceGroup,
    DataSourcesCatalog,
)
from quick_map_services.gui.qms_settings_page import QmsSettingsPageFactory
from quick_map_services.notifier.message_bar_notifier import MessageBarNotifier
from quick_map_services.qgis_map_helpers import add_data_source_to_map
from quick_map_services.qms_service_toolbox import QmsServiceToolbox
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)
from quick_map_services.ui_kit.icons import (
    material_icon,
    plugin_icon,
    qgis_icon,
)

if TYPE_CHECKING:
    from quick_map_services.notifier.notifier_interface import (
        NotifierInterface,
    )

    assert isinstance(iface, QgisInterface)  # nosec B101


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

        # Create the dialog (after translation) and keep reference
        self.info_dlg = AboutDialog(
            PACKAGE_NAME, components_path=self.path / "assets/components.json"
        )
        self.info_dlg.developer_mode_toggle_requested.connect(
            self._toggle_developer_mode
        )

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
        self.qms_search_action = None
        self.qms_search_toolbar_action = None
        self.data_sources_catalog = DataSourcesCatalog()

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        :rtype: NotifierInterface
        :raises AssertionError: If notifier is not initialized.
        """
        assert self._notifier is not None, "Notifier is not initialized"  # nosec B101
        return self._notifier

    @staticmethod
    def tr(message: str) -> str:
        """Translate a QuickMapServices user-facing string.

        :param message: Source text to translate.

        :returns: Translated text.
        """
        return QCoreApplication.translate("QuickMapServices", message)

    def _load(self) -> None:
        """
        Initialize the QuickMapServices plugin GUI.
        """
        self._add_translator(
            self.path / "i18n" / f"{PLUGIN_NAME}_{utils.qgis_locale()}.qm",
        )
        self._notifier = MessageBarNotifier(self)

        # Create menu
        self.menu = QMenu(PLUGIN_NAME)
        self.menu.setIcon(plugin_icon())
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
        xml_root = ET.parse(scales_filename).getroot()  # noqa: S314 # nosec
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

    def _toggle_developer_mode(self) -> None:
        """Ask for confirmation and toggle the persistent developer mode."""
        settings = QmsSettings()
        is_enabled = settings.is_developer_mode_enabled
        question = self.tr(
            "Disable developer mode?"
            if is_enabled
            else "Enable developer mode?"
        )
        details = self.tr(
            "Developer mode is intended for plugin development and may expose "
            "experimental features."
        )
        response = QMessageBox.question(
            self.info_dlg,
            PLUGIN_NAME,
            f"{question}\n\n{details}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        settings.is_developer_mode_enabled = not is_enabled
        message = self.tr(
            "Developer mode disabled."
            if is_enabled
            else "Developer mode enabled."
        )
        self.notifier.display_message(
            message,
            level=Qgis.MessageLevel.Info,
            duration=5,
        )

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
        self.data_sources_catalog = None
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
    qms_banner_action = None
    set_nearest_scale_act = None
    settings_act = None
    info_act = None

    def build_menu_tree(self) -> None:
        """
        Build the QuickMapServices main plugin menu in QGIS.

        :return: None
        """
        self.menu.clear()

        self.data_sources_catalog.reload()
        hidden_data_source_ids = QmsSettings().hidden_datasource_id_list
        all_service_groups = self.data_sources_catalog.grouped_services(
            DataSourceCategory.all,
            hidden_data_source_ids,
        )
        self._add_qms_section()
        self._populate_data_sources_menu(self.menu, all_service_groups)
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
            self.tb_action = None

        if self.qms_search_toolbar_action:
            self.iface.webToolBar().removeAction(
                self.qms_search_toolbar_action
            )
            self.iface.layerToolBar().removeAction(
                self.qms_search_toolbar_action
            )
            self.qms_search_toolbar_action = None

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
        toolbar = self.iface.webToolBar()
        toolbutton = QToolButton(toolbar)
        toolbutton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbutton.setMenu(self.menu)
        toolbutton.setIcon(self.menu.icon())
        toolbutton.setIconSize(toolbar.iconSize())
        toolbutton.setText(self.menu.title())
        toolbutton.setToolTip(self.menu.title())
        toolbutton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbutton.setAutoRaise(True)
        toolbutton.setStyleSheet(
            "QToolButton::menu-indicator {image: none;width: 0px;}"
        )
        # self.tb_action = toolbutton.defaultAction()
        # print "self.tb_action: ", self.tb_action

        self.tb_action = toolbar.addWidget(toolbutton)
        search_toolbutton = QToolButton(toolbar)
        search_toolbutton.setDefaultAction(self.qms_search_action)
        search_toolbutton.setIconSize(toolbar.iconSize())
        search_toolbutton.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        search_toolbutton.setAutoRaise(True)
        self.qms_search_toolbar_action = toolbar.addWidget(search_toolbutton)
        self._sync_toolbar_button_sizes()

    def _sync_toolbar_button_sizes(self) -> None:
        """Make custom toolbar buttons equal size."""
        toolbar = self.iface.webToolBar()
        buttons = []
        for action in (self.tb_action, self.qms_search_toolbar_action):
            if action is None:
                continue

            button = toolbar.widgetForAction(action)
            if isinstance(button, QToolButton):
                buttons.append(button)

        if len(buttons) < 2:
            return

        button_size = max(
            max(button.sizeHint().width(), button.sizeHint().height())
            for button in buttons
        )
        for button in buttons:
            button.setFixedSize(button_size, button_size)

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
        icon_settings_path = self.plugin_dir + "/icons/qms_logo.svg"
        self.qms_search_action = QAction(self.iface.mainWindow())
        self.qms_search_action.setCheckable(True)
        self.qms_search_action.setIcon(QIcon(icon_settings_path))
        self.qms_search_action.setText(self.tr("Search NextGIS QMS"))
        self.qms_search_action.setChecked(self.server_toolbox.isUserVisible())
        self.qms_search_action.triggered.connect(
            self.server_toolbox.setUserVisible
        )
        self.server_toolbox.visibilityChanged.connect(
            lambda _visible: self.qms_search_action.setChecked(
                self.server_toolbox.isUserVisible()
            )
        )

    def remove_server_panel(self) -> None:
        """
        Remove the QMS Server panel (dock widget) from QGIS.
        """
        if not hasattr(self, "server_toolbox"):
            return

        self.iface.removeDockWidget(self.server_toolbox)
        self.server_toolbox.close()
        self.server_toolbox.setParent(None)
        self.server_toolbox.deleteLater()
        self.server_toolbox = None

    def openURL(self) -> None:
        """
        Open the QMS create page in the default web browser.

        :return: None
        """
        settings = QmsSettings()
        QDesktopServices.openUrl(QUrl(f"{settings.endpoint_url}/create"))

    def _make_nextgis_data_url(self) -> str:
        short_locale = utils.qgis_locale(adapt=False)
        utm_parts = [
            "utm_source=qgis_plugin",
            "utm_medium=banner",
            "utm_campaign=constant",
            f"utm_term={PACKAGE_NAME}",
            f"utm_content={short_locale}",
        ]
        return f"https://data.nextgis.com/?{'&'.join(utm_parts)}"

    def open_nextgis_data_url(self) -> None:
        QDesktopServices.openUrl(QUrl(self._make_nextgis_data_url()))

    def _nextgis_data_action_text(self) -> str:
        return self.tr("Download geodata for your project")

    def _populate_data_sources_menu(
        self,
        menu: QMenu,
        groups: Iterable[DataSourceGroup],
    ) -> None:
        """Populate a menu with grouped data-source actions.

        :param menu: Menu to populate.
        :param groups: Ordered groups of visible data sources.
        """
        for group in groups:
            group_menu = menu.addMenu(
                QIcon(group.info.icon),
                self.tr(group.info.alias),
            )
            for data_source in group.data_sources:
                action = group_menu.addAction(
                    QIcon(data_source.icon_path),
                    self.tr(data_source.alias),
                )
                action.triggered.connect(
                    lambda _checked, source=data_source: (
                        add_data_source_to_map(source)
                    )
                )

    def _add_qms_section(self) -> None:
        """
        Add QMS service section to menu.

        :return: None
        """
        self.menu.addSeparator()

        self.service_actions.append(self.qms_search_action)
        self.menu.addAction(self.qms_search_action)

        if not self.qms_create_service_action:
            self.qms_create_service_action = QAction(
                self.tr("Contribute a Service"),
                self.iface.mainWindow(),
            )
            self.qms_create_service_action.setIcon(material_icon("publish"))
            self.qms_create_service_action.setToolTip(
                self.tr("Submit a new map service to the QMS catalog")
            )
            self.qms_create_service_action.triggered.connect(self.openURL)

        self.menu.addAction(self.qms_create_service_action)
        self.menu.addSeparator()

        if not self.qms_banner_action:
            icon_path = f"{self.plugin_dir}/icons/news.png"
            self.qms_banner_action = QAction(
                self._nextgis_data_action_text(),
                self.iface.mainWindow(),
            )
            self.qms_banner_action.setIcon(QIcon(icon_path))
            self.qms_banner_action.triggered.connect(
                self.open_nextgis_data_url
            )

        self.menu.addAction(self.qms_banner_action)
        self.menu.addSeparator()

    def _add_plugin_actions(self) -> None:
        """
        Add plugin-related actions to the menu.

        :return: None
        """
        self.menu.addSeparator()

        if not self.set_nearest_scale_act:
            self.set_nearest_scale_act = QAction(
                qgis_icon("mActionSetToCanvasScale.svg"),
                self.tr("Set nearest SlippyMap scale"),
                self.iface.mainWindow(),
            )
            self.set_nearest_scale_act.triggered.connect(
                self.set_nearest_scale
            )
            self.service_actions.append(self.set_nearest_scale_act)

        self.menu.addAction(self.set_nearest_scale_act)

        if not self.settings_act:
            self.settings_act = QAction(
                qgis_icon("iconSettingsConsole.svg"),
                self.tr("Settings"),
                self.iface.mainWindow(),
            )
            self.settings_act.triggered.connect(self.show_settings_dialog)
            self.service_actions.append(self.settings_act)

        self.menu.addAction(self.settings_act)

        if not self.info_act:
            self.info_act = QAction(
                qgis_icon("mActionPropertiesWidget.svg"),
                self.tr("About QMS"),
                self.iface.mainWindow(),
            )
            self.info_act.triggered.connect(self.info_dlg.show)
            self.service_actions.append(self.info_act)

        self.menu.addAction(self.info_act)

        self._help_action = QAction(
            QIcon(f"{self.plugin_dir}/icons/qms_logo.svg"),
            PLUGIN_NAME,
        )
        self._help_action.triggered.connect(self.info_dlg.show)

        plugin_help_menu = self.iface.pluginHelpMenu()
        if plugin_help_menu is None:
            logger.error("Failed to get plugin help menu")
            return
        plugin_help_menu.addAction(self._help_action)
