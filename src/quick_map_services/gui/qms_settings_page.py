from pathlib import Path
from typing import List, Optional

from qgis.gui import (
    QgsOptionsPageWidget,
    QgsOptionsWidgetFactory,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QHeaderView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from quick_map_services.core.constants import COMPANY_NAME, PLUGIN_NAME
from quick_map_services.core.exceptions import QmsUiLoadError
from quick_map_services.core.logging import logger, update_logging_level
from quick_map_services.core.settings import QmsSettings
from quick_map_services.data_sources_model import DSManagerModel
from quick_map_services.gui.user_groups_box import UserGroupsBox
from quick_map_services.gui.user_services_box import UserServicesBox
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)


class QmsSettingsPage(QgsOptionsPageWidget):
    """
    QMS plugin settings page integrated into QGIS Options dialog.

    Loads the original .ui-based settings interface and connects
    QMS settings, data source model, and extra services actions.
    """

    _ds_model: DSManagerModel

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the settings page widget.

        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)

        self._ds_model = DSManagerModel()

        self._load_ui()
        self._load_settings()

    def apply(self) -> None:
        """
        Save current settings when user confirms changes.

        :return: None
        :rtype: None
        """
        settings = QmsSettings()

        settings.enable_otf_3857 = self._widget.chkEnableOTF3857.isChecked()
        self._save_other(settings)

        self._ds_model.saveSettings()

        plugin = QuickMapServicesInterface.instance()
        plugin.settings_changed.emit()

    def cancel(self) -> None:
        """Cancel changes made in the settings page."""

    def _load_ui(self) -> None:
        """Load .ui file and prepare layout."""
        widget: Optional[QWidget] = None
        try:
            widget = uic.loadUi(
                str(Path(__file__).parent / "qms_settings_page_base.ui")
            )
        except Exception as error:
            raise QmsUiLoadError from error

        if widget is None:
            raise QmsUiLoadError

        self._widget = widget
        self._widget.setParent(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self._widget)

        layout = self._widget.tab_user_groups_and_services.layout()
        layout.addWidget(
            UserGroupsBox(self._widget.tab_user_groups_and_services)
        )
        layout.addWidget(
            UserServicesBox(self._widget.tab_user_groups_and_services)
        )

        self._widget.treeViewForDS.setModel(self._ds_model)
        self._widget.treeViewForDS.sortByColumn(
            self._ds_model.COLUMN_GROUP_DS, Qt.SortOrder.AscendingOrder
        )

        self._widget.treeViewForDS.header().setSectionResizeMode(
            self._ds_model.COLUMN_GROUP_DS, QHeaderView.ResizeMode.Stretch
        )

        check_all_action = self._widget.toolBarForDSTreeView.addAction(
            QIcon(":/images/themes/default/mActionShowAllLayers.svg"),
            self.tr("Show all"),
        )
        check_all_action.triggered.connect(self._ds_model.checkAll)

        uncheck_all_action = self._widget.toolBarForDSTreeView.addAction(
            QIcon(":/images/themes/default/mActionHideAllLayers.svg"),
            self.tr("Hide all"),
        )
        uncheck_all_action.triggered.connect(self._ds_model.uncheckAll)

    def _load_settings(self) -> None:
        """Initialize widget state and signal connections."""
        settings = QmsSettings()

        self._widget.chkEnableOTF3857.setChecked(settings.enable_otf_3857)
        self._widget.debug_logs_checkbox.setChecked(
            settings.is_debug_logs_enabled
        )

    def _save_other(self, settings: QmsSettings) -> None:
        old_debug_enabled = settings.is_debug_logs_enabled
        new_debug_enabled = self._widget.debug_logs_checkbox.isChecked()
        settings.is_debug_logs_enabled = new_debug_enabled
        if old_debug_enabled != new_debug_enabled:
            debug_state = "enabled" if new_debug_enabled else "disabled"
            update_logging_level()
            logger.warning(f"Debug messages were {debug_state}")


class QmsSettingsErrorPage(QgsOptionsPageWidget):
    """Error page shown if settings page fails to load.

    Displays an error message in the options dialog.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the error page widget.

        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)

        self.widget = QLabel(
            self.tr("An error occurred while loading settings page"), self
        )
        self.widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.widget)

    def apply(self) -> None:
        """Apply changes (no-op for error page)."""

    def cancel(self) -> None:
        """Cancel changes (no-op for error page)."""


class QmsSettingsPageFactory(QgsOptionsWidgetFactory):
    """
    Factory registering QMS options page under QGIS Options dialog.
    """

    def __init__(self) -> None:
        """Initialize the settings page factory."""
        super().__init__()
        self.setTitle(PLUGIN_NAME)

        icon_path = str(Path(__file__).parents[1] / "icons" / "qms_logo.svg")
        self.setIcon(QIcon(icon_path))

    def path(self) -> List[str]:
        """Return the settings page path in the options dialog.

        :returns: List of path elements.
        :rtype: List[str]
        """
        return [COMPANY_NAME]

    def createWidget(
        self, parent: Optional[QWidget] = None
    ) -> Optional[QgsOptionsPageWidget]:
        """
        Create and return the QMS options widget or error page.

        :param parent: Parent widget
        :type parent: Optional[QWidget]

        :return: Initialized QMS options or error page
        :rtype: QgsOptionsPageWidget
        """
        try:
            return QmsSettingsPage(parent)
        except Exception:
            logger.exception("An error occurred while loading settings page")
            return QmsSettingsErrorPage(parent)
