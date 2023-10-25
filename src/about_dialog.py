import os
from typing import Dict, Optional

from qgis.PyQt.QtCore import QLocale
from qgis.PyQt.QtWidgets import QWidget, QDialog
from qgis.PyQt import uic
from qgis.core import QgsSettings
from qgis.utils import pluginMetadata

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "about_dialog_base.ui")
)


class AboutDialog(QDialog, FORM_CLASS):
    def __init__(self, package_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__package_name = package_name

        replacemens = self.__replacemens()
        self.pluginName.setText(self.pluginName.text().replace(
            "{plugin_name}", replacemens["{plugin_name}"])
        )
        self.setWindowTitle(self.windowTitle().format(
            plugin_name=replacemens["{plugin_name}"]
        ))
        html = self.textBrowser.toHtml()
        for key, value in replacemens.items():
            html = html.replace(key, value)
        self.textBrowser.setHtml(html)

    def __locale(self) -> str:
        override_locale = QgsSettings().value(
            "locale/overrideFlag", False, type=bool
        )
        if not override_locale:
            locale_full_name = QLocale.system().name()
        else:
            locale_full_name = QgsSettings().value("locale/userLocale", "")

        return locale_full_name[0:2]

    def __replacemens(self) -> Dict[str, str]:
        locale = self.__locale()
        is_ru = locale in ["ru", "uk"]

        def metadata_value(key: str) -> str:
            value = pluginMetadata(self.__package_name, f"{key}[{locale}]")
            if value == '__error__':
                value = pluginMetadata(self.__package_name, key)
            return value

        about = metadata_value("about")
        about_stop_phrase = "Разработан компанией" if is_ru else "Developed by"
        if about.find(about_stop_phrase) > 0:
            about = about[:about.find(about_stop_phrase)]

        return {
            "{plugin_name}": metadata_value("name"),
            "{description}": metadata_value("description"),
            "{about}": about,
            "{authors}": metadata_value("author"),
            "{video_url}": metadata_value("video"),
            "{homepage_url}": metadata_value("repository"),
            "{tracker_url}": metadata_value("tracker"),
            "{main_url}": f"https://nextgis.{'ru' if is_ru else 'com'}",
        }
