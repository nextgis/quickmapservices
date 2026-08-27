# NextGIS Plugin
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

import importlib.util
import json
import re
from enum import Enum
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Dict, Optional, Union

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import (
    QByteArray,
    QEvent,
    QLocale,
    QObject,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QHideEvent,
    QIcon,
    QPainter,
    QPixmap,
)
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import pluginMetadata

__all__ = ["AboutDialog"]

_BALANCE_ICON = r'<svg xmlns="http://www.w3.org/2000/svg" height="48px" viewBox="0 -960 960 960" width="48px" fill="#ffffff"><path d="M80-120v-60h370v-484q-26-9-46.5-29.5T374-740H215l125 302q-1 45-38.5 76.5T210-330q-54 0-91.5-31.5T80-438l125-302h-85v-60h254q12-35 41-57.5t65-22.5q36 0 65 22.5t41 57.5h254v60h-85l125 302q-1 45-38.5 76.5T750-330q-54 0-91.5-31.5T620-438l125-302H586q-9 26-29.5 46.5T510-664v484h370v60H80Zm595-320h150l-75-184-75 184Zm-540 0h150l-75-184-75 184Zm345-280q21 0 35.5-15t14.5-35q0-21-14.5-35.5T480-820q-20 0-35 14.5T430-770q0 20 15 35t35 15Z"/></svg>'
_DESCRIPTION_ICON = r'<svg fill="#ffffff" xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path d="M319-250h322v-60H319v60Zm0-170h322v-60H319v60ZM220-80q-24 0-42-18t-18-42v-680q0-24 18-42t42-18h361l219 219v521q0 24-18 42t-42 18H220Zm331-554v-186H220v680h520v-494H551ZM220-820v186-186 680-680Z"/></svg>'
_NEXTGIS_LOGO_ICON = r'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" id="svg2" x="0" y="0" viewBox="3.2 1.9 20.1 20.5"><style>.st0{fill:#231f20}</style><g id="layer1" transform="translate(0 -924.362)"><path id="path4131-1" d="m15.5 939.3-1.6 2.3 3.4 5.2h5.9l-3.4-4.8-3.1-4.5z" class="st0"/><path id="path4131" d="m8.9 946.8 7.2-10.2-7.2-10.2H3.2l7.2 10.3-7.1 10.2h5.6z" style="fill:#176fc1"/><path id="path4131-1-1" d="m15.8 928.9-1.9 2.7 2.8 4 6.5-9.3h-5.6z" class="st0"/></g></svg> '
_OPEN_IN_NEW_ICON = r'<svg xmlns="http://www.w3.org/2000/svg" height="40px" viewBox="0 -960 960 960" width="40px" fill="#ffffff"><path d="M186.67-120q-27 0-46.84-19.83Q120-159.67 120-186.67v-586.66q0-27 19.83-46.84Q159.67-840 186.67-840H466v66.67H186.67v586.66h586.66V-466H840v279.33q0 27-19.83 46.84Q800.33-120 773.33-120H186.67ZM384-336.67 337.33-384l389.34-389.33h-194V-840H840v307.33h-66.67V-726L384-336.67Z"/></svg>'

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    " by NextGIS": {
        "de": " von NextGIS",
        "en": " by NextGIS",
        "es": " por NextGIS",
        "fr": " par NextGIS",
        "it": " di NextGIS",
        "ja": " NextGIS によって作成",
        "pt": " da NextGIS",
        "ru": " от NextGIS",
    },
    "About {plugin_name}": {
        "de": "Über {plugin_name}",
        "en": "About {plugin_name}",
        "es": "Acerca de {plugin_name}",
        "fr": "À propos du {plugin_name}",
        "it": "Riguardo {plugin_name}",
        "ja": "{plugin_name}について",
        "pt": "Acerca da {plugin_name}",
        "ru": "О модуле {plugin_name}",
    },
    "Components": {
        "de": "Komponenten",
        "en": "Components",
        "es": "Componentes",
        "fr": "Composants",
        "it": "Componenti",
        "ja": "コンポーネント",
        "pt": "Componentes",
        "ru": "Компоненты",
    },
    "Contributors": {
        "de": "Mitwirkende",
        "en": "Contributors",
        "es": "Colaboradores",
        "fr": "Contributeurs",
        "it": "Collaboratori",
        "ja": "寄稿者",
        "pt": "Contribuidores",
        "ru": "Участники",
    },
    "Convenient up-to-date data extracts for any place in the world": {
        "de": "Praktische, aktuelle Datenauszüge für jeden Ort der Welt",
        "en": "Convenient up-to-date data extracts for any place in the world",
        "es": "Extractos de datos actualizados convenientes para cualquier lugar del mundo",
        "fr": "Des extraits de données pratiques et actualisés pour tous lieux dans le monde",
        "it": "Comodi estratti di dati aggiornati per qualsiasi luogo del mondo",
        "ja": "世界のあらゆる場所のための便利な最新のデータ抽出",
        "pt": "Extratos de dados atualizados convenientes para qualquer lugar do mundo",
        "ru": "Удобная выборка актуальных данных из любой точки мира",
    },
    "Developers": {
        "de": "Entwickler",
        "en": "Developers",
        "es": "Desarrolladores",
        "fr": "Développeurs",
        "it": "Sviluppatori",
        "ja": "開発者",
        "pt": "Desenvolvedores",
        "ru": "Разработчики",
    },
    "Fully featured Web GIS service": {
        "de": "Web-GIS-Dienst mit vollem Funktionsumfang",
        "en": "Fully featured Web GIS service",
        "es": "Servicio Web GIS con todas las funciones",
        "fr": "Service SIG Web entièrement équipé",
        "it": "Servizio Web GIS completo",
        "ja": "完全な機能を備えたWeb GISサービス",
        "pt": "Serviço Web GIS com todas as funcionalidades",
        "ru": "Полнофункциональный Веб ГИС-сервис",
    },
    "Get involved": {
        "de": "Mitmachen",
        "en": "Get involved",
        "es": "Participe",
        "fr": "S'impliquer",
        "it": "Partecipare",
        "ja": "参加しよう",
        "pt": "Envolver-se",
        "ru": "Присоединяйтесь",
    },
    "Homepage": {
        "de": "Startseite",
        "en": "Homepage",
        "es": "Página de inicio",
        "fr": "Page d'accueil",
        "it": "Pagina iniziale",
        "ja": "ホームページ",
        "pt": "Página inicial",
        "ru": "Домашняя страница",
    },
    "Information": {
        "de": "Informationen",
        "en": "Information",
        "es": "Información",
        "fr": "Information",
        "it": "Informazioni",
        "ja": "情報",
        "pt": "Informação",
        "ru": "Информация",
    },
    "Join the community": {
        "de": "Der Community beitreten",
        "en": "Join the community",
        "es": "Únase a la comunidad",
        "fr": "Rejoindre la communauté",
        "it": "Unisciti alla comunità",
        "pt": "Junte-se à comunidade",
        "ru": "Сообщество",
    },
    "License": {
        "de": "Lizenz",
        "en": "License",
        "es": "Licencia",
        "fr": "Licence",
        "it": "Licenza",
        "ja": "ライセンス",
        "pt": "Licença",
        "ru": "Лицензия",
    },
    "License page": {
        "de": "Lizenzseite",
        "en": "License page",
        "es": "Página de licencia",
        "fr": "Page de la licence",
        "it": "Pagina della licenza",
        "pt": "Página da licença",
        "ru": "Страница лицензии",
    },
    "Other helpful services by NextGIS": {
        "de": "Weitere nützliche Dienste von NextGIS",
        "en": "Other helpful services by NextGIS",
        "es": "Otros servicios útiles de NextGIS",
        "fr": "Autres services utiles de NextGIS",
        "it": "Altri servizi utili di NextGIS",
        "ja": "NextGISのその他の便利なサービス",
        "pt": "Outros serviços úteis da NextGIS",
        "ru": "Другие полезные сервисы от NextGIS",
    },
    "Please report bugs at {tracker_link}": {
        "de": "Bitte melden Sie Fehler unter {tracker_link}",
        "en": "Please report bugs at {tracker_link}",
        "es": "Por favor, informe de errores en {tracker_link}",
        "fr": "Veuillez signaler les bogues à {tracker_link}",
        "it": "Si prega di segnalare i bug a {tracker_link}",
        "ja": "{tracker_link}でバグを報告してください",
        "pt": "Por favor, reportar bugs em {tracker_link}",
        "ru": "Пожалуйста, сообщайте об ошибках в {tracker_link}",
    },
    "Project page": {
        "de": "Projektseite",
        "en": "Project page",
        "es": "Página del proyecto",
        "fr": "Page du projet",
        "it": "Pagina del progetto",
        "pt": "Página do projeto",
        "ru": "Страница проекта",
    },
    "User Guide": {
        "de": "Benutzerhandbuch",
        "en": "User Guide",
        "es": "Guía del usuario",
        "fr": "Guide de l'utilisateur",
        "it": "Guida per l'utente",
        "ja": "ユーザーガイド",
        "pt": "Guia do utilizador",
        "ru": "Руководство пользователя",
    },
    "Version {version}": {
        "de": "Version {version}",
        "en": "Version {version}",
        "es": "Versión {version}",
        "fr": "Version {version}",
        "it": "Versione {version}",
        "ja": "バージョン {version}",
        "pt": "Versão {version}",
        "ru": "Версия {version}",
    },
    "Video with an overview of the plugin": {
        "de": "Video mit einem Überblick über das Plugin",
        "en": "Video with an overview of the plugin",
        "es": "Vídeo con una visión general del plugin",
        "fr": "Vidéo avec un aperçu du plugin",
        "it": "Video con una panoramica del plugin",
        "ja": "プラグインの概要ビデオ",
        "pt": "Vídeo com uma visão geral do plugin",
        "ru": "Видео с обзором плагина",
    },
    "bugtracker": {
        "de": "Bugtracker",
        "en": "bugtracker",
        "es": "bugtracker",
        "fr": "traqueur de bogues",
        "it": "bugtracker",
        "ja": "バグトラッカー",
        "pt": "rastreador de erros",
        "ru": "багтрекер",
    },
}

_URL_RE = re.compile(
    r"\b(?:https?://[^\s<>()]+|www\.[^\s<>()]+|"
    r"(?<!@)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,24}(?:/[^\s<>()]*)?)",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _locale() -> str:
    override_locale = QgsSettings().value(
        "locale/overrideFlag", defaultValue=False, type=bool
    )
    if not override_locale:
        locale_full_name = QLocale.system().name()
    else:
        locale_full_name = QgsSettings().value("locale/userLocale", "")
    locale_name = locale_full_name[0:2].lower()

    return locale_name if locale_name.lower() != "c" else "en"


@lru_cache(maxsize=1)
def _is_russian_speaking() -> bool:
    return _locale() in ["be", "kk", "ky", "ru", "uk"]


def _nextgis_domain(subdomain: Optional[str] = None) -> str:
    if subdomain is None:
        subdomain = ""
    elif not subdomain.endswith("."):
        subdomain += "."
    domain_zone = "ru" if _is_russian_speaking() else "com"
    return f"https://{subdomain}nextgis.{domain_zone}"


def _render_svg_icon(
    svg: Union[Path, str],
    *,
    color: Optional[str] = None,
    size: Optional[int] = None,
    replacements: Optional[Dict[str, str]] = None,
) -> QIcon:
    if isinstance(svg, Path):
        svg_content = svg.read_text(encoding="utf-8")
    else:
        svg_content = svg

    if color:
        modified_svg = svg_content.replace('fill="#ffffff"', f'fill="{color}"')
        modified_svg = modified_svg.replace('fill="#fff"', f'fill="{color}"')
        modified_svg = modified_svg.replace("fill:#ffffff", f"fill:{color}")
        modified_svg = modified_svg.replace("fill:#fff", f"fill:{color}")
    else:
        modified_svg = svg_content

    if replacements:
        for key, value in replacements.items():
            modified_svg = modified_svg.replace(key, value)

    byte_array = QByteArray(modified_svg.encode("utf-8"))
    renderer = QSvgRenderer()
    if not renderer.load(byte_array):
        message = f"Failed to load SVG: {svg}"
        raise ValueError(message)

    target_size = renderer.defaultSize() if size is None else QSize(size, size)
    pixmap = QPixmap(target_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(
        painter,
        QRectF(0, 0, target_size.width(), target_size.height()),
    )
    painter.end()

    return QIcon(pixmap)


class _AboutTab(str, Enum):
    Information = "information_tab"
    License = "license_tab"
    Components = "components_tab"
    Contributors = "contributors_tab"

    def __str__(self) -> str:
        return str(self.value)


class AboutDialog(QDialog):
    """Show plugin information and component metadata.

    Display package metadata, license text, component information, and
    contributor links in a tabbed dialog.
    """

    _COMPONENT_ITEM_HEIGHT = 64
    _COMPONENT_BUTTON_ICON_SIZE = 16
    _COMPONENT_BUTTON_SIZE = 22
    _TAB_ICON_SIZE = 16
    _DEVELOPER_MODE_CLICKS = 7
    _DEVELOPER_MODE_CLICK_INTERVAL_MS = 1500

    developer_mode_toggle_requested = pyqtSignal()

    def __init__(
        self,
        package_name: str,
        parent: Optional[QWidget] = None,
        components_path: Optional[Union[Path, str]] = None,
    ) -> None:
        """Initialize the about dialog.

        :param package_name: Python package name used for metadata lookup.
        :param parent: Parent widget.
        :param components_path: Path to component metadata JSON.
        """
        super().__init__(parent)
        self._package_name = package_name
        self._components_path = (
            Path(components_path) if components_path is not None else None
        )
        self._version_click_count = 0
        self._version_click_timer = QTimer(self)
        self._version_click_timer.setSingleShot(True)
        self._version_click_timer.timeout.connect(self._reset_version_clicks)

        module_spec = importlib.util.find_spec(self._package_name)
        if module_spec and module_spec.origin:
            self._package_path = Path(module_spec.origin).parent
        else:
            self._package_path = Path(__file__).parent

        self._setup_ui()
        self._tab_widget.setCurrentIndex(0)

        metadata = self._metadata()
        self._set_icon(metadata)
        self._fill_headers(metadata)
        self._fill_get_involved(metadata)
        self._fill_about(metadata)
        self._fill_license()
        self._fill_components()
        self._fill_contributors()

    def _setup_ui(self) -> None:
        self._window_title_template = self._text("About {plugin_name}")
        self.setWindowTitle(self._window_title_template)
        self.resize(652, 512)

        grid_layout = QGridLayout(self)
        grid_layout.setObjectName("gridLayout")
        grid_layout.setVerticalSpacing(12)

        self._header_layout = QHBoxLayout()
        self._header_layout.setObjectName("header_layout")
        self._header_layout.setSpacing(9)

        self._info_layout = QVBoxLayout()
        self._info_layout.setObjectName("info_layout")
        self._info_layout.setSpacing(3)

        self._plugin_name_label = QLabel("{plugin_name}", self)
        self._plugin_name_label.setObjectName("plugin_name_label")
        font = self._plugin_name_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self._plugin_name_label.setFont(font)
        self._plugin_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_layout.addWidget(self._plugin_name_label)

        self._version_label = QLabel(self._text("Version {version}"), self)
        self._version_label.setObjectName("version_label")
        self._version_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._version_label.installEventFilter(self)
        self._info_layout.addWidget(self._version_label)

        self._header_layout.addLayout(self._info_layout)
        self._header_layout.addStretch(1)
        grid_layout.addLayout(self._header_layout, 0, 0)

        self._tab_widget = QTabWidget(self)
        self._tab_widget.setObjectName("tab_widget")
        self._tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self._tab_widget.setDocumentMode(False)

        self._information_tab = QWidget(self._tab_widget)
        self._information_tab.setObjectName(str(_AboutTab.Information))
        information_layout = QVBoxLayout(self._information_tab)
        information_layout.setObjectName("information_layout")
        information_layout.setContentsMargins(0, 0, 0, 0)

        self._about_text_browser = QTextBrowser(self._information_tab)
        self._about_text_browser.setObjectName("about_text_browser")
        self._about_text_browser.setReadOnly(True)
        self._about_text_browser.setOpenExternalLinks(True)
        self._about_text_browser.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        information_layout.addWidget(self._about_text_browser)

        self._license_tab = QWidget(self._tab_widget)
        self._license_tab.setObjectName(str(_AboutTab.License))
        license_layout = QVBoxLayout(self._license_tab)
        license_layout.setObjectName("license_layout")
        license_layout.setContentsMargins(0, 0, 0, 0)

        self._license_text_browser = QTextBrowser(self._license_tab)
        self._license_text_browser.setObjectName("license_text_browser")
        license_layout.addWidget(self._license_text_browser)

        self._components_tab = QWidget(self._tab_widget)
        self._components_tab.setObjectName(str(_AboutTab.Components))
        components_layout = QVBoxLayout(self._components_tab)
        components_layout.setObjectName("components_layout")
        components_layout.setContentsMargins(0, 0, 0, 0)

        self._components_list_widget = QListWidget(self._components_tab)
        self._components_list_widget.setObjectName("components_list_widget")
        self._components_list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._components_list_widget.setSpacing(6)
        components_layout.addWidget(self._components_list_widget)

        self._contributors_tab = QWidget(self._tab_widget)
        self._contributors_tab.setObjectName(str(_AboutTab.Contributors))
        contributors_layout = QVBoxLayout(self._contributors_tab)
        contributors_layout.setObjectName("contributors_layout")
        contributors_layout.setContentsMargins(0, 0, 0, 0)

        self._contributors_text_browser = QTextBrowser(self._contributors_tab)
        self._contributors_text_browser.setObjectName(
            "contributors_text_browser"
        )
        contributors_layout.addWidget(self._contributors_text_browser)

        self._tab_widget.addTab(
            self._information_tab, self._text("Information")
        )
        self._tab_widget.addTab(self._license_tab, self._text("License"))
        self._tab_widget.addTab(self._components_tab, self._text("Components"))
        self._tab_widget.addTab(
            self._contributors_tab, self._text("Contributors")
        )
        self._setup_tab_icons()
        grid_layout.addWidget(self._tab_widget, 2, 0)

        self._footer_layout = QHBoxLayout()
        self._footer_layout.setObjectName("footer_layout")
        self._footer_layout.setContentsMargins(0, 0, 0, 0)

        self._get_involved_button = QPushButton(
            self._text("Get involved"), self
        )
        self._get_involved_button.setObjectName("get_involved_button")
        self._get_involved_button.setIcon(
            _render_svg_icon(_NEXTGIS_LOGO_ICON, size=18)
        )
        self._get_involved_button.setIconSize(QSize(18, 18))
        self._get_involved_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._footer_layout.addWidget(self._get_involved_button)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            Qt.Orientation.Horizontal,
            self,
        )
        self._button_box.setObjectName("button_box")
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self._footer_layout.addWidget(self._button_box)
        grid_layout.addLayout(self._footer_layout, 3, 0)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Request a developer-mode toggle after repeated version clicks."""
        if (
            watched is self._version_label
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._version_click_count += 1
            if self._version_click_count == self._DEVELOPER_MODE_CLICKS:
                self._reset_version_clicks()
                self.developer_mode_toggle_requested.emit()
            else:
                self._version_click_timer.start(
                    self._DEVELOPER_MODE_CLICK_INTERVAL_MS
                )

        return super().eventFilter(watched, event)

    def hideEvent(self, event: QHideEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Discard incomplete click sequences when the dialog is hidden."""
        self._reset_version_clicks()
        super().hideEvent(event)

    def _reset_version_clicks(self) -> None:
        self._version_click_timer.stop()
        self._version_click_count = 0

    def _setup_tab_icons(self) -> None:
        icon_color = self.palette().text().color().name()
        description_icon = _render_svg_icon(
            _DESCRIPTION_ICON,
            color=icon_color,
            size=self._TAB_ICON_SIZE,
        )
        balance_icon = _render_svg_icon(
            _BALANCE_ICON,
            color=icon_color,
            size=self._TAB_ICON_SIZE,
        )
        self._set_tab_icon(_AboutTab.Information, description_icon)
        self._set_tab_icon(_AboutTab.License, balance_icon)
        self._set_tab_icon(_AboutTab.Components, balance_icon)

    def _set_tab_icon(self, tab_name: _AboutTab, icon: QIcon) -> None:
        tab_index = self._tab_to_index(tab_name)
        if tab_index >= 0:
            self._tab_widget.setTabIcon(tab_index, icon)

    def _fill_headers(self, metadata: Dict[str, Optional[str]]) -> None:
        plugin_name = metadata.get("plugin_name") or self._package_name
        if "NextGIS" not in plugin_name:
            plugin_name += self._text(" by NextGIS")

        header_metadata = dict(metadata)
        header_metadata["plugin_name"] = plugin_name
        header_metadata["version"] = header_metadata.get("version") or ""

        self.setWindowTitle(
            self._window_title_template.format(plugin_name=plugin_name)
        )
        self._plugin_name_label.setText(
            self._plugin_name_label.text().format_map(header_metadata)
        )
        self._version_label.setText(
            self._version_label.text().format_map(header_metadata)
        )

    def _set_icon(self, metadata: Dict[str, Optional[str]]) -> None:
        icon_path_value = metadata.get("icon_path")
        if icon_path_value is None:
            return

        header_height = max(self._info_layout.sizeHint().height(), 48)
        icon_path = self._package_path / icon_path_value
        svg_icon_path = icon_path.with_suffix(".svg")

        if svg_icon_path.exists():
            icon = QIcon(str(svg_icon_path))
            pixmap = icon.pixmap(QSize(header_height, header_height))
        else:
            pixmap = QPixmap(str(icon_path))
            if pixmap.isNull():
                return

            pixmap = pixmap.scaled(
                QSize(header_height, header_height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        icon_widget = QLabel(self)
        icon_widget.setPixmap(pixmap)
        icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_widget.setFixedSize(pixmap.size())
        self._header_layout.insertWidget(0, icon_widget)

    def _fill_get_involved(self, metadata: Dict[str, Optional[str]]) -> None:
        get_involved_url = metadata.get("get_involved_url")
        if not get_involved_url:
            self._get_involved_button.setEnabled(False)
            return

        self._get_involved_button.clicked.connect(
            lambda checked=False, url=get_involved_url: (
                QDesktopServices.openUrl(QUrl(url))
            )
        )

    def _fill_about(self, metadata: Dict[str, Optional[str]]) -> None:
        self._about_text_browser.setHtml(self._html(metadata))

    def _fill_license(self) -> None:
        license_path = self._package_path / "LICENSE"
        if not license_path.exists():
            self._remove_tab(_AboutTab.License)
            return

        self._license_text_browser.setPlainText(
            license_path.read_text(encoding="utf-8")
        )

    def _fill_components(self) -> None:
        components_path = self._components_path
        if components_path is None or not components_path.exists():
            self._remove_tab(_AboutTab.Components)
            return

        try:
            components_data = json.loads(
                components_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            self._remove_tab(_AboutTab.Components)
            return

        if not isinstance(components_data, list):
            self._remove_tab(_AboutTab.Components)
            return

        self._components_list_widget.clear()
        self._components_list_widget.setUniformItemSizes(True)
        self._components_list_widget.setSpacing(2)

        for component_data in components_data:
            if not isinstance(component_data, dict):
                continue

            item_widget = self._component_item_widget(component_data)
            if item_widget is None:
                continue

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, self._COMPONENT_ITEM_HEIGHT))
            self._components_list_widget.addItem(item)
            self._components_list_widget.setItemWidget(item, item_widget)

        if self._components_list_widget.count() == 0:
            self._remove_tab(_AboutTab.Components)

    def _fill_contributors(self) -> None:
        self._remove_tab(_AboutTab.Contributors)

    def _component_item_widget(
        self, component_data: Dict[str, Any]
    ) -> Optional[QWidget]:
        title = self._component_text(component_data, "title")
        description = self._component_text(component_data, "description")
        license_url = self._component_text(component_data, "license_url")
        project_url = self._component_text(component_data, "project_url")

        if None in (title, description, license_url, project_url):
            return None

        assert title is not None
        assert description is not None
        assert license_url is not None
        assert project_url is not None

        version = self._component_text(component_data, "version")

        item_widget = QWidget(self._components_list_widget)
        item_widget.setFixedHeight(self._COMPONENT_ITEM_HEIGHT)

        content_layout = QHBoxLayout(item_widget)
        content_layout.setContentsMargins(8, 4, 8, 4)
        content_layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        title_label = QLabel(item_widget)
        title_label.setTextFormat(Qt.TextFormat.RichText)
        title_label.setWordWrap(True)
        title_label.setText(self._component_title(title, version))
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        description_label = QLabel(description, item_widget)
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        full_title = title if version is None else f"{title} ({version})"
        title_label.setToolTip(full_title)
        description_label.setToolTip(description)

        text_layout.addWidget(title_label)
        text_layout.addWidget(description_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)

        license_button = self._component_button(
            icon=_BALANCE_ICON,
            url=license_url,
            title=self._text("License page"),
        )
        project_button = self._component_button(
            icon=_OPEN_IN_NEW_ICON,
            url=project_url,
            title=self._text("Project page"),
        )

        buttons_layout.addWidget(license_button)
        buttons_layout.addWidget(project_button)

        content_layout.addLayout(text_layout, 1)
        content_layout.addLayout(buttons_layout)

        return item_widget

    def _component_button(
        self, *, icon: str, url: str, title: str
    ) -> QToolButton:
        button = QToolButton(self._components_list_widget)
        button.setAutoRaise(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setIcon(
            _render_svg_icon(
                icon,
                color=self.palette().text().color().name(),
                size=self._COMPONENT_BUTTON_ICON_SIZE,
            )
        )
        button.setIconSize(
            QSize(
                self._COMPONENT_BUTTON_ICON_SIZE,
                self._COMPONENT_BUTTON_ICON_SIZE,
            )
        )
        button.setFixedSize(
            QSize(self._COMPONENT_BUTTON_SIZE, self._COMPONENT_BUTTON_SIZE)
        )
        button.setToolTip(f"{title}: {url}")
        button.clicked.connect(
            lambda checked=False, url=url: QDesktopServices.openUrl(QUrl(url))
        )
        return button

    def _component_text(
        self, component_data: Dict[str, Any], key: str
    ) -> Optional[str]:
        value = component_data.get(key)
        if isinstance(value, str):
            normalized_value = value.strip()
            return normalized_value or None

        if not isinstance(value, dict):
            return None

        localized_value = value.get(_locale(), value.get("en"))
        if not isinstance(localized_value, str):
            return None

        normalized_value = localized_value.strip()
        return normalized_value or None

    def _component_title(self, title: str, version: Optional[str]) -> str:
        escaped_title = escape(title)
        if version is None:
            return f'<span style="font-weight: 600;">{escaped_title}</span>'

        escaped_version = escape(version)
        return (
            f'<span style="font-weight: 600;">{escaped_title}</span> '
            f"({escaped_version})"
        )

    def _metadata(self) -> Dict[str, Optional[str]]:
        locale_name = _locale()

        def metadata_value(key: str) -> Optional[str]:
            value = pluginMetadata(self._package_name, f"{key}[{locale_name}]")
            if value == "__error__":
                value = pluginMetadata(self._package_name, key)
            if value == "__error__":
                value = None
            return value

        about = metadata_value("about") or ""
        for about_stop_phrase in (
            "Разработан",
            "Developed by",
            "Développé par",
            "Desarrollado por",
            "Sviluppato da",
            "Desenvolvido por",
            "Entwickelt von",
        ):
            phrase_position = about.find(about_stop_phrase)
            if phrase_position > 0:
                about = about[:phrase_position]

        package_name = self._package_name.replace("qgis_", "")
        main_url = _nextgis_domain()
        utm = (
            "utm_source=qgis_plugin&utm_medium=about"
            f"&utm_campaign=constant&utm_term={package_name}"
            f"&utm_content={locale_name}"
        )

        return {
            "plugin_name": metadata_value("name") or self._package_name,
            "version": metadata_value("version") or "",
            "icon_path": metadata_value("icon"),
            "description": metadata_value("description"),
            "about": about,
            "authors": metadata_value("author") or "NextGIS",
            "video_url": metadata_value("video"),
            "homepage_url": metadata_value("homepage"),
            "tracker_url": metadata_value("tracker"),
            "user_guide_url": metadata_value("user_guide"),
            "main_url": main_url,
            "data_url": main_url.replace("://", "://data."),
            "get_involved_url": (
                f"https://nextgis.com/redirect/{locale_name}/ak45prp5?{utm}"
            ),
            "community_url": "https://community.nextgis.com",
            "utm": utm,
            "speaks_russian": str(_is_russian_speaking()),
        }

    def _html(self, metadata: Dict[str, Optional[str]]) -> str:
        parts = [
            self._plain_text_html(metadata.get("description")),
            self._plain_text_html(metadata.get("about")),
        ]

        user_guide_url = metadata.get("user_guide_url")
        if user_guide_url:
            parts.append(
                self._info_link(
                    self._text("User Guide"),
                    self._url_with_query(user_guide_url, metadata["utm"]),
                    user_guide_url,
                )
            )

        main_url = metadata.get("main_url")
        authors = metadata.get("authors")
        if main_url and authors:
            parts.append(
                self._info_link(
                    self._text("Developers"),
                    self._url_with_query(main_url, metadata["utm"]),
                    authors,
                )
            )

        homepage_url = metadata.get("homepage_url")
        if homepage_url:
            parts.append(
                self._info_link(
                    self._text("Homepage"),
                    homepage_url,
                    homepage_url,
                )
            )

        community_url = metadata.get("community_url")
        if community_url:
            parts.append(
                self._info_link(
                    self._text("Join the community"),
                    self._url_with_query(community_url, metadata["utm"]),
                    community_url,
                )
            )

        tracker_url = metadata.get("tracker_url")
        if tracker_url:
            tracker_link = self._link(tracker_url, self._text("bugtracker"))
            parts.append(
                f"<p>{self._html_text('Please report bugs at {tracker_link}', tracker_link=tracker_link)}</p>"
            )

        video_url = metadata.get("video_url")
        if video_url:
            parts.append(
                self._info_link(
                    self._text("Video with an overview of the plugin"),
                    video_url,
                    video_url,
                )
            )

        data_url = metadata.get("data_url")
        if main_url and data_url:
            webgis_url = f"{main_url}/nextgis-com/plans"
            parts.append(
                "<p>"
                f"{escape(self._text('Other helpful services by NextGIS'))}:"
                "</p>"
                "<ul>"
                "<li>"
                f"<b>{escape(self._text('Convenient up-to-date data extracts for any place in the world'))}</b>: "
                f"{self._link(self._url_with_query(data_url, metadata['utm']), data_url)}"
                "</li>"
                "<li>"
                f"<b>{escape(self._text('Fully featured Web GIS service'))}</b>: "
                f"{self._link(self._url_with_query(webgis_url, metadata['utm']), webgis_url)}"
                "</li>"
                "</ul>"
            )

        return (
            "<!DOCTYPE html>"
            "<html><head><meta charset='utf-8'>"
            "<style>"
            "body { font-family: sans-serif; font-size: 9pt; }"
            "p { margin-top: 0; margin-bottom: 8px; }"
            "ul { margin-top: 0; margin-bottom: 8px; }"
            "a { text-decoration: underline; }"
            "</style></head><body>"
            f"{''.join(parts)}"
            "</body></html>"
        )

    def _plain_text_html(self, text: Optional[str]) -> str:
        if text is None:
            return ""

        lines = [
            line.strip()
            for line in text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        ]

        result = []
        in_list = False
        for line in lines:
            if not line:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                continue

            if line.startswith(("- ", "* ")):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                result.append(f"<li>{self._linkify_plain_text(line[2:])}</li>")
                continue

            if in_list:
                result.append("</ul>")
                in_list = False

            result.append(f"<p>{self._linkify_plain_text(line)}</p>")

        if in_list:
            result.append("</ul>")

        return "".join(result)

    def _linkify_plain_text(self, text: str) -> str:
        result = []
        position = 0
        for match in _URL_RE.finditer(text):
            raw_url = match.group(0)
            url = raw_url.rstrip(".,;:!?)]}")
            trailing = raw_url[len(url) :]

            result.append(escape(text[position : match.start()]))
            result.append(self._link(self._url_href(url), url))
            result.append(escape(trailing))
            position = match.end()

        result.append(escape(text[position:]))
        return "".join(result)

    def _info_link(self, title: str, url: str, label: str) -> str:
        return f"<p><b>{escape(title)}:</b> {self._link(url, label)}</p>"

    def _link(self, url: str, label: str) -> str:
        return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'

    def _url_href(self, url: str) -> str:
        if url.lower().startswith(("http://", "https://")):
            return url
        return f"https://{url}"

    def _url_with_query(self, url: str, query: Optional[str]) -> str:
        if not query:
            return url

        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{query.lstrip('?')}"

    def _html_text(self, source: str, **html_values: str) -> str:
        return escape(self._text(source)).format_map(html_values)

    def _text(self, source: str) -> str:
        translations = _TRANSLATIONS.get(source)
        if translations is None:
            return source

        return translations.get(_locale(), translations.get("en", source))

    def _tab_to_index(self, tab_name: _AboutTab) -> int:
        tab = self._tab_widget.findChild(QWidget, str(tab_name))
        return self._tab_widget.indexOf(tab)

    def _remove_tab(self, tab_name: _AboutTab) -> None:
        tab_index = self._tab_to_index(tab_name)
        if tab_index >= 0:
            self._tab_widget.removeTab(tab_index)
