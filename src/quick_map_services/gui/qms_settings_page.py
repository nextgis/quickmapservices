from pathlib import Path
from typing import List, Optional

from qgis.core import Qgis, QgsApplication, QgsMessageLog
from qgis.gui import (
    QgsOptionsPageWidget,
    QgsOptionsWidgetFactory,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QHeaderView,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from quick_map_services.core.constants import COMPANY_NAME, PLUGIN_NAME
from quick_map_services.core.settings import QmsSettings
from quick_map_services.data_sources_model import DSManagerModel
from quick_map_services.extra_sources import ExtraSources
from quick_map_services.gui.user_groups_box import UserGroupsBox
from quick_map_services.gui.user_services_box import UserServicesBox


class QmsSettingsPage(QgsOptionsPageWidget):
    """
    QMS plugin settings page integrated into QGIS Options dialog.

    Loads the original .ui-based settings interface and connects
    QMS settings, data source model, and extra services actions.
    """

    __ds_model: DSManagerModel

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the settings page widget.

        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        """
        super().__init__(parent)

        self.__ds_model = DSManagerModel()

        self.__load_ui()
        self.__load_settings()

    def apply(self) -> None:
        """
        Save current settings when user confirms changes.

        :return: None
        :rtype: None
        """
        settings = QmsSettings()

        settings.enable_otf_3857 = self.__widget.chkEnableOTF3857.isChecked()
        settings.show_messages_in_bar = (
            self.__widget.chkShowMessagesInBar.isChecked()
        )

        self.__ds_model.saveSettings()

    def cancel(self) -> None:
        """Cancel changes made in the settings page."""

    def __load_ui(self) -> None:
        """Load .ui file and prepare layout."""
        widget: Optional[QWidget] = None
        try:
            widget = uic.loadUi(
                str(Path(__file__).parent / "qms_settings_page_base.ui")
            )
        except Exception as error:
            QgsMessageLog.logMessage(
                str(error), PLUGIN_NAME, level=Qgis.Critical
            )
            raise RuntimeError from error

        if widget is None:
            message = self.tr("An error occured in settings UI")
            QgsMessageLog.logMessage(message, PLUGIN_NAME, level=Qgis.Critical)
            raise RuntimeError

        self.__widget = widget
        self.__widget.setParent(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self.__widget)

        layout = self.__widget.tab_user_groups_and_services.layout()
        layout.addWidget(
            UserGroupsBox(self.__widget.tab_user_groups_and_services)
        )
        layout.addWidget(
            UserServicesBox(self.__widget.tab_user_groups_and_services)
        )

        self.__widget.treeViewForDS.setModel(self.__ds_model)
        self.__widget.treeViewForDS.sortByColumn(
            self.__ds_model.COLUMN_GROUP_DS, Qt.SortOrder.AscendingOrder
        )

        self.__widget.treeViewForDS.header().setSectionResizeMode(
            self.__ds_model.COLUMN_GROUP_DS, QHeaderView.ResizeMode.Stretch
        )

        check_all_action = self.__widget.toolBarForDSTreeView.addAction(
            QIcon(":/images/themes/default/mActionShowAllLayers.svg"),
            self.tr("Show all"),
        )
        check_all_action.triggered.connect(self.__ds_model.checkAll)

        uncheck_all_action = self.__widget.toolBarForDSTreeView.addAction(
            QIcon(":/images/themes/default/mActionHideAllLayers.svg"),
            self.tr("Hide all"),
        )
        uncheck_all_action.triggered.connect(self.__ds_model.uncheckAll)

        self.__widget.btnGetContribPack.clicked.connect(
            self._on_get_contrib_pack
        )

    def __load_settings(self) -> None:
        """Initialize widget state and signal connections."""
        settings = QmsSettings()

        self.__widget.chkEnableOTF3857.setChecked(settings.enable_otf_3857)
        self.__widget.chkShowMessagesInBar.setChecked(
            settings.show_messages_in_bar
        )

    @pyqtSlot()
    def _on_get_contrib_pack(self) -> None:
        """Get contributed pack."""
        QgsApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ExtraSources().load_contrib_pack()
            QgsApplication.restoreOverrideCursor()

            info_message = self.tr(
                "The latest version of contributed pack was successfully downloaded!"
            )
            QMessageBox.information(self, PLUGIN_NAME, info_message)

            self.__ds_model.resetModel()

        except Exception as error:
            QgsApplication.restoreOverrideCursor()

            error_message = self.tr(
                "Failed to load contributed pack:\n{}"
            ).format(str(error))
            QMessageBox.critical(self, PLUGIN_NAME, error_message)

        finally:
            QgsApplication.restoreOverrideCursor()


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
            return QmsSettingsErrorPage(parent)
