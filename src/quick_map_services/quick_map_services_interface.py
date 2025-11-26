import configparser
from abc import abstractmethod
from pathlib import Path

from qgis import utils
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QObject, QTranslator

from quick_map_services.shared.qobject_metaclass import QObjectMetaClass


class QuickMapServicesInterface(QObject, metaclass=QObjectMetaClass):
    """Interface for the QuickMapServices plugin.

    This abstract base class provides singleton access to the plugin
    instance, exposes plugin metadata, version, and path, and defines
    abstract properties and methods that must be implemented by concrete
    subclasses.
    """

    @classmethod
    def instance(cls) -> "QuickMapServicesInterface":
        """Return the singleton instance of the QuickMapServicesInterface plugin.

        :returns: The QuickMapServicesInterface plugin instance.
        :rtype: QuickMapServicesInterface
        :raises AssertionError: If the plugin has not been created yet.
        """
        plugin = utils.plugins.get("quick_map_services")
        assert plugin is not None, "Using a plugin before it was created"
        return plugin

    @property
    def metadata(self) -> configparser.ConfigParser:
        """Return the parsed metadata for the plugin.

        :returns: Parsed metadata as a ConfigParser object.
        :rtype: configparser.ConfigParser
        """
        metadata = utils.plugins_metadata_parser.get("quick_map_services")
        assert metadata is not None, "Using a plugin before it was created"
        return metadata

    @property
    def version(self) -> str:
        """Return the plugin version.

        :returns: Plugin version string.
        :rtype: str
        """
        return self.metadata.get("general", "version")

    @property
    def path(self) -> "Path":
        """Return the plugin path.

        :returns: Path to the plugin directory.
        :rtype: Path
        """
        return Path(__file__).parent

    def initGui(self) -> None:
        """Initialize the GUI components and load necessary resources."""
        self.__translators = list()

        self._load()

    def unload(self) -> None:
        """Unload the plugin and perform cleanup operations."""
        self._unload()

        self.__unload_translations()

    @abstractmethod
    def _load(self) -> None:
        """Load the plugin resources and initialize components.

        This method must be implemented by subclasses.
        """
        ...

    @abstractmethod
    def _unload(self) -> None:
        """Unload the plugin resources and clean up components.

        This method must be implemented by subclasses.
        """
        ...

    def _add_translator(self, translator_path: Path) -> None:
        """Add a translator for the plugin.

        :param translator_path: Path to the translation file.
        :type translator_path: Path
        """
        translator = QTranslator()
        is_loaded = translator.load(str(translator_path))
        if not is_loaded:
            return

        is_installed = QgsApplication.installTranslator(translator)
        if not is_installed:
            return

        # Should be kept in memory
        self.__translators.append(translator)

    def __unload_translations(self) -> None:
        """Remove all translators added by the plugin."""
        for translator in self.__translators:
            QgsApplication.removeTranslator(translator)
        self.__translators.clear()
