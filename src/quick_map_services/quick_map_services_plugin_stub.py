from typing import Optional

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject
from qgis.utils import iface

from quick_map_services.core.settings import QmsSettings
from quick_map_services.plugin_locale import Locale
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)

assert isinstance(iface, QgisInterface)


class QuickMapServicesPluginStub(QuickMapServicesInterface):
    """Stub implementation of plugin interface used to notify the user when the plugin failed to start."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Initialize the plugin stub."""
        super().__init__(parent)

    def _load(self) -> None:
        """Load the plugin resources and initialize components."""
        locale = Locale.get_locale()
        self._add_translator(
            self.path / "i18n" / f"{QmsSettings.PRODUCT}_{locale}.qm",
        )

    def _unload(self) -> None:
        """Unload the plugin resources and clean up components."""
        pass
