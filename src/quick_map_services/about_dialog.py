from enum import Enum
from importlib.util import find_spec
from pathlib import Path
from typing import Dict, Optional

from qgis.core import QgsSettings
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QT_VERSION_STR, QFile, QLocale, QSize, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QDialog, QLabel, QWidget
from qgis.utils import pluginMetadata

QT_MAJOR_VERSION = int(QT_VERSION_STR.split(".")[0])
if QT_MAJOR_VERSION < 6:
    from qgis.PyQt.QtSvg import QSvgWidget
elif find_spec("qgis.PyQt.QtSvgWidgets"):
    from qgis.PyQt.QtSvgWidgets import QSvgWidget
else:
    from PyQt6.QtSvgWidgets import QSvgWidget

CURRENT_PATH = Path(__file__).parent
UI_PATH = Path(__file__).parent / "ui"
RESOURCES_PATH = Path(__file__).parents[1] / "resources"

if (UI_PATH / "about_dialog_base.ui").exists():
    Ui_AboutDialogBase, _ = uic.loadUiType(
        str(UI_PATH / "about_dialog_base.ui")
    )
elif (UI_PATH / "aboutdialogbase.ui").exists():
    Ui_AboutDialogBase, _ = uic.loadUiType(str(UI_PATH / "aboutdialogbase.ui"))
elif (RESOURCES_PATH / "about_dialog_base.ui").exists():
    Ui_AboutDialogBase, _ = uic.loadUiType(
        str(RESOURCES_PATH / "about_dialog_base.ui")
    )
elif (CURRENT_PATH / "about_dialog_base.ui").exists():
    Ui_AboutDialogBase, _ = uic.loadUiType(
        str(CURRENT_PATH / "about_dialog_base.ui")
    )
elif (UI_PATH / "about_dialog_base.py").exists():
    from .ui.about_dialog_base import (  # type: ignore
        Ui_AboutDialogBase,
    )
elif (UI_PATH / "aboutdialogbase.py").exists():
    from .ui.aboutdialogbase import (  # type: ignore
        Ui_AboutDialogBase,
    )
elif (UI_PATH / "ui_aboutdialogbase.py").exists():
    from .ui.ui_aboutdialogbase import (  # type: ignore
        Ui_AboutDialogBase,
    )
else:
    raise ImportError


class AboutTab(str, Enum):
    Information = "information_tab"
    License = "license_tab"
    Components = "components_tab"
    Contributors = "contributors_tab"

    def __str__(self) -> str:
        return str(self.value)


class AboutDialog(QDialog, Ui_AboutDialogBase):
    def __init__(self, package_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__package_name = package_name

        self.tab_widget.setCurrentIndex(0)

        metadata = self.__metadata()
        self.__set_icon(metadata)
        self.__fill_headers(metadata)
        self.__fill_get_involved(metadata)
        self.__fill_about(metadata)
        self.__fill_license()
        self.__fill_components()
        self.__fill_contributors()

    def __fill_headers(self, metadata: Dict[str, Optional[str]]) -> None:
        plugin_name = metadata["plugin_name"]
        assert isinstance(plugin_name, str)
        if "NextGIS" not in plugin_name:
            plugin_name += self.tr(" by NextGIS")

        self.setWindowTitle(self.windowTitle().format(plugin_name=plugin_name))
        self.plugin_name_label.setText(
            self.plugin_name_label.text().format_map(metadata)
        )
        self.version_label.setText(
            self.version_label.text().format_map(metadata)
        )

    def __set_icon(self, metadata: Dict[str, Optional[str]]) -> None:
        if metadata.get("icon_path") is None:
            return

        header_size: QSize = self.info_layout.sizeHint()

        icon_path = Path(__file__).parent / str(metadata.get("icon_path"))
        svg_icon_path = icon_path.with_suffix(".svg")

        if svg_icon_path.exists():
            icon_widget: QWidget = QSvgWidget(str(svg_icon_path), self)
            icon_size: QSize = icon_widget.sizeHint()
        else:
            pixmap = QPixmap(str(icon_path))
            if pixmap.size().height() > header_size.height():
                pixmap = pixmap.scaled(
                    header_size.height(),
                    header_size.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                )

            icon_size: QSize = pixmap.size()

            icon_widget = QLabel(self)
            icon_widget.setPixmap(pixmap)
            icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_size.scale(
            header_size.height(),
            header_size.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        )
        icon_widget.setFixedSize(icon_size)
        self.header_layout.insertWidget(0, icon_widget)

    def __fill_get_involved(self, metadata: Dict[str, Optional[str]]) -> None:
        plugin_path = Path(__file__).parent
        file_path = str(plugin_path / "icons" / "nextgis_logo.svg")
        resources_path = (
            f":/plugins/{self.__package_name}/icons/nextgis_logo.svg"
        )

        if QFile(resources_path).exists():
            self.get_involved_button.setIcon(QIcon(resources_path))
        elif QFile(file_path).exists():
            self.get_involved_button.setIcon(QIcon(file_path))

        self.get_involved_button.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(metadata["get_involved_url"])
            )
        )

    def __fill_about(self, metadata: Dict[str, Optional[str]]) -> None:
        self.about_text_browser.setHtml(self.__html(metadata))

    def __fill_license(self) -> None:
        license_path = Path(__file__).parent / "LICENSE"
        if not license_path.exists():
            self.tab_widget.removeTab(self.__tab_to_index(AboutTab.License))
            return

        self.license_text_browser.setPlainText(license_path.read_text())

    def __fill_components(self) -> None:
        self.tab_widget.removeTab(self.__tab_to_index(AboutTab.Components))

    def __fill_contributors(self) -> None:
        self.tab_widget.removeTab(self.__tab_to_index(AboutTab.Contributors))

    def __locale(self) -> str:
        override_locale = QgsSettings().value(
            "locale/overrideFlag", defaultValue=False, type=bool
        )
        if not override_locale:
            locale_full_name = QLocale.system().name()
        else:
            locale_full_name = QgsSettings().value("locale/userLocale", "")

        return locale_full_name[0:2]

    def __metadata(self) -> Dict[str, Optional[str]]:
        locale = self.__locale()
        speaks_russian = locale in ["be", "kk", "ky", "ru", "uk"]

        def metadata_value(key: str) -> Optional[str]:
            value = pluginMetadata(self.__package_name, f"{key}[{locale}]")
            if value == "__error__":
                value = pluginMetadata(self.__package_name, key)
            if value == "__error__":
                value = None
            return value

        about = metadata_value("about")
        assert about is not None
        for about_stop_phrase in (
            "Разработан",
            "Developed by",
            "Développé par",
            "Desarrollado por",
            "Sviluppato da",
            "Desenvolvido por",
        ):
            if about.find(about_stop_phrase) > 0:
                about = about[: about.find(about_stop_phrase)]

        package_name = self.__package_name.replace("qgis_", "")

        main_url = f"https://nextgis.{'ru' if speaks_russian else 'com'}"
        utm = f"utm_source=qgis_plugin&utm_medium=about&utm_campaign=constant&utm_term={package_name}&utm_content={locale}"

        return {
            "plugin_name": metadata_value("name"),
            "version": metadata_value("version"),
            "icon_path": metadata_value("icon"),
            "description": metadata_value("description"),
            "about": about,
            "authors": metadata_value("author"),
            "video_url": metadata_value("video"),
            "homepage_url": metadata_value("homepage"),
            "tracker_url": metadata_value("tracker"),
            "main_url": main_url,
            "data_url": main_url.replace("://", "://data."),
            "get_involved_url": f"https://nextgis.com/redirect/{locale}/ak45prp5?{utm}",
            "utm": f"?{utm}",
            "speaks_russian": str(speaks_russian),
        }

    def __html(self, metadata: Dict[str, Optional[str]]) -> str:
        report_end = self.tr("REPORT_END")
        if report_end == "REPORT_END":
            report_end = ""

        titles = {
            "developers_title": self.tr("Developers"),
            "homepage_title": self.tr("Homepage"),
            "report_title": self.tr("Please report bugs at"),
            "report_end": report_end,
            "bugtracker_title": self.tr("bugtracker"),
            "video_title": self.tr("Video with an overview of the plugin"),
            "services_title": self.tr("Other helpful services by NextGIS"),
            "extracts_title": self.tr(
                "Convenient up-to-date data extracts for any place in the world"
            ),
            "webgis_title": self.tr("Fully featured Web GIS service"),
        }

        description = """
            <p>{description}</p>
            <p>{about}</p>
            <p><b>{developers_title}:</b> <a href="{main_url}/{utm}">{authors}</a></p>
            <p><b>{homepage_title}:</b> <a href="{homepage_url}">{homepage_url}</a></p>
            <p><b>{report_title}</b> <a href="{tracker_url}">{bugtracker_title}</a> {report_end}</p>
            """

        if metadata.get("video_url") is not None:
            description += '<p><b>{video_title}:</b> <a href="{video_url}">{video_url}</a></p>'

        services = """
            <p>
            {services_title}:
            <ul>
              <li><b>{extracts_title}</b>: <a href="{data_url}/{utm}">{data_url}</a></li>
              <li><b>{webgis_title}</b>: <a href="{main_url}/nextgis-com/plans{utm}">{main_url}/nextgis-com/plans</a></li>
            </ul>
            </p>
            """

        replacements = dict()
        replacements.update(titles)
        replacements.update(metadata)

        return (description + services).format_map(replacements)

    def __tab_to_index(self, tab_name: AboutTab) -> int:
        tab = self.tab_widget.findChild(QWidget, str(tab_name))
        return self.tab_widget.indexOf(tab)
