import sys
from typing import TYPE_CHECKING, Optional

from osgeo import gdal
from qgis.core import Qgis
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QT_VERSION_STR, QObject, QSysInfo
from qgis.utils import iface

from quick_map_services.core import utils
from quick_map_services.core.constants import PLUGIN_NAME
from quick_map_services.core.logging import logger
from quick_map_services.notifier.message_bar_notifier import MessageBarNotifier
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)

if TYPE_CHECKING:
    from quick_map_services.notifier.notifier_interface import (
        NotifierInterface,
    )

assert isinstance(iface, QgisInterface)


class QuickMapServicesPluginStub(QuickMapServicesInterface):
    """Stub implementation of plugin interface used to notify the user when the plugin failed to start."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Initialize the plugin stub."""
        super().__init__(parent)
        metadata_file = self.path / "metadata.txt"

        logger.debug("<b>✓ Plugin stub created</b>")
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

        self.__notifier = None

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        :rtype: NotifierInterface
        """
        assert self.__notifier is not None, "Notifier is not initialized"
        return self.__notifier

    def _load(self) -> None:
        """Load the plugin resources and initialize components."""
        self._add_translator(
            self.path / "i18n" / f"{PLUGIN_NAME}_{utils.locale()}.qm",
        )
        self.__notifier = MessageBarNotifier(self)

    def _unload(self) -> None:
        """Unload the plugin resources and clean up components."""
        self.__notifier.deleteLater()
        self.__notifier = None
