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

import ast
import sys
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from os import path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import URLError

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsSettings,
)
from qgis.gui import QgisInterface, QgsDockWidget
from qgis.PyQt import uic
from qgis.PyQt.QtCore import (
    QByteArray,
    QEvent,
    QMutex,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from qgis.PyQt.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from quick_map_services.core import utils
from quick_map_services.core.constants import PACKAGE_NAME
from quick_map_services.core.logging import logger
from quick_map_services.core.settings import QmsSettings
from quick_map_services.data_source_info import DataSourceCategory
from quick_map_services.data_source_serializer import DataSourceSerializer
from quick_map_services.data_sources_catalog import DataSourcesCatalog
from quick_map_services.qgis_map_helpers import (
    add_data_source_to_map,
    add_layer_to_map,
)
from quick_map_services.qms_external_api_python.api.api_base import QmsNews
from quick_map_services.qms_external_api_python.client import Client
from quick_map_services.qms_news import News, NewsLayout
from quick_map_services.quick_map_services_interface import (
    QuickMapServicesInterface,
)
from quick_map_services.rb_result_renderer import RubberBandResultRenderer
from quick_map_services.singleton import singleton
from quick_map_services.ui_kit.buttons.animated import ButtonVisualState
from quick_map_services.ui_kit.buttons.shining import ShiningButton
from quick_map_services.ui_kit.icons import material_icon

SERVICE_LIST_MODE_FAVORITES = "favorites"
SERVICE_LIST_MODE_RECENT = "recent"
QT_WIDGET_MAX_SIZE = 16777215

SEARCH_LAYOUT_SPACING = 4
SERVICE_RESULT_CARD_OUTER_MARGIN = 2
SERVICE_RESULT_CARD_BORDER_RADIUS = 3
SERVICE_RESULT_CONTROL_BORDER_RADIUS = 2
SERVICE_RESULT_CARD_MARGIN_HORIZONTAL = 6
SERVICE_RESULT_CARD_MARGIN_VERTICAL = 6
SERVICE_RESULT_CARD_MAIN_SPACING = SERVICE_RESULT_CARD_MARGIN_HORIZONTAL
SERVICE_RESULT_CONTENT_SPACING = SERVICE_RESULT_CARD_MARGIN_HORIZONTAL
SERVICE_RESULT_NAME_SPACING = SERVICE_RESULT_CARD_MARGIN_HORIZONTAL
SERVICE_RESULT_META_SPACING = SERVICE_RESULT_CARD_MARGIN_HORIZONTAL
SERVICE_RESULT_BADGE_PADDING_HORIZONTAL = 6
SERVICE_RESULT_BADGE_PADDING_VERTICAL = 1
SERVICE_RESULT_ADD_PADDING_HORIZONTAL = 4
SERVICE_RESULT_ADD_PADDING_VERTICAL = 4
SERVICE_RESULT_ICON_SIZE = 42
SERVICE_RESULT_ICON_PIXMAP_SIZE = 36
SERVICE_RESULT_ADD_ICON_SIZE = 16
SERVICE_RESULT_ADD_COMPACT_SIZE = 30
SERVICE_RESULT_FAVORITE_ICON_SIZE = 12
SERVICE_RESULT_NAME_ELIDE_PADDING = 4
SERVICE_RESULT_NAME_MIN_ELIDE_WIDTH = 40
NEWS_BANNER_BORDER_RADIUS = 3
NEWS_BANNER_MARGIN_HORIZONTAL = 0
NEWS_BANNER_MARGIN_VERTICAL = 0
NEWS_BANNER_PADDING_HORIZONTAL = 6
NEWS_BANNER_PADDING_VERTICAL = 6
NEWS_BANNER_MINIMUM_HEIGHT = 30
NEWS_BANNER_MINIMUM_WIDTH = 160
NEWS_BANNER_ICON_SIZE = 16
NEWS_BANNER_ICON_TEXT_SPACING = 5
NEWS_BANNER_SHIMMER_ALPHA = 2
NEWS_BANNER_SHIMMER_BAND_MIN_WIDTH = 32
NEWS_BANNER_NORMAL_BACKGROUND_ALPHA = 12
NEWS_BANNER_HOVER_BACKGROUND_ALPHA = 0
NEWS_BANNER_PRESSED_BACKGROUND_ALPHA = 46
NEWS_BANNER_NORMAL_BORDER_ALPHA = 58
TOOL_BUTTON_BORDER_RADIUS = SERVICE_RESULT_CONTROL_BORDER_RADIUS
TOOL_BUTTON_ICON_SIZE = 16
UI_NEUTRAL_BACKGROUND = "rgba(127, 127, 127, 28)"
UI_NEUTRAL_BACKGROUND_SOFT = "rgba(127, 127, 127, 18)"
UI_NEUTRAL_BACKGROUND_HOVER = "rgba(127, 127, 127, 44)"
UI_NEUTRAL_BACKGROUND_PRESSED = "rgba(127, 127, 127, 64)"
UI_NEUTRAL_BORDER = "rgba(127, 127, 127, 104)"
UI_NEUTRAL_BORDER_SOFT = "rgba(127, 127, 127, 72)"


def add_geoservice_to_map(
    geoservice: Dict[str, Any],
    image_ba: QByteArray,
    service_not_found_callback: Optional[Callable[[int], None]] = None,
    service_unavailable_callback: Optional[Callable[[str], None]] = None,
    service_added_callback: Optional[Callable[[], None]] = None,
) -> None:
    try:
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        client = Client()

        try:
            geoservice_info = client.get_geoservice_info(geoservice)
        except ConnectionError as error:
            error_code, message = error.args
            service_id = geoservice.get("id")

            if error_code in (
                QNetworkReply.NetworkError.ContentNotFoundError,
                QNetworkReply.NetworkError.ContentGoneError,
            ):
                if service_not_found_callback is not None and isinstance(
                    service_id, int
                ):
                    service_not_found_callback(service_id)
                return

            if service_unavailable_callback is not None:
                service_unavailable_callback(message)
            return

        except ValueError:
            if service_unavailable_callback is not None:
                service_unavailable_callback(
                    QgsApplication.translate(
                        "QmsServiceToolbox", "Failed to read service data"
                    )
                )
            return

        data_source = DataSourceSerializer.read_from_json(geoservice_info)
        add_layer_to_map(data_source, qms_id=geoservice["id"])
        CachedServices().add_service(geoservice, image_ba)
        if service_added_callback is not None:
            service_added_callback()

    except Exception as error:
        logger.exception("An error occured while adding geoservice to the map")
        QuickMapServicesInterface.instance().notifier.display_exception(error)
    finally:
        QApplication.restoreOverrideCursor()


class UiPaletteHelper:
    """Palette-based color helpers for compact controls."""

    @staticmethod
    def muted_icon_color(widget: QWidget) -> str:
        return UiPaletteHelper._mixed_text_color(widget, 0.68)

    @staticmethod
    def active_icon_color(widget: QWidget) -> str:
        return UiPaletteHelper._mixed_text_color(widget, 0.92)

    @staticmethod
    def mixed_text_qcolor(widget: QWidget, color_ratio: float) -> QColor:
        foreground_color = QColor(widget.palette().text().color())
        background_color = QColor(widget.palette().window().color())
        background_ratio = 1.0 - color_ratio

        return QColor(
            round(
                foreground_color.red() * color_ratio
                + background_color.red() * background_ratio
            ),
            round(
                foreground_color.green() * color_ratio
                + background_color.green() * background_ratio
            ),
            round(
                foreground_color.blue() * color_ratio
                + background_color.blue() * background_ratio
            ),
        )

    @staticmethod
    def _mixed_text_color(widget: QWidget, color_ratio: float) -> str:
        return UiPaletteHelper.mixed_text_qcolor(widget, color_ratio).name()


class NewsBannerHtmlParser(HTMLParser):
    """Extract a click URL and display text from the legacy news HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.url = ""
        self.image_path = ""
        self.fragments: List[Tuple[str, bool]] = []
        self._anchor_depth = 0
        self._bold_depth = 0

    @property
    def display_html(self) -> str:
        parts = []
        for text, is_bold in self.fragments:
            escaped_text = escape(text)
            if is_bold:
                escaped_text = f"<b>{escaped_text}</b>"

            parts.append(escaped_text)

        return " ".join(parts)

    @property
    def plain_text(self) -> str:
        return " ".join(text for text, _ in self.fragments)

    def handle_starttag(
        self,
        tag: str,
        attrs: List[Tuple[str, Optional[str]]],
    ) -> None:
        tag_name = tag.casefold()
        if tag_name == "a":
            self._anchor_depth += 1
            self._store_anchor_url(attrs)
            return

        if tag_name == "img":
            self._store_image_path(attrs)
            return

        if tag_name in ("b", "strong"):
            self._bold_depth += 1

    def handle_startendtag(
        self,
        tag: str,
        attrs: List[Tuple[str, Optional[str]]],
    ) -> None:
        del attrs
        if tag.casefold() == "br":
            self._append_text(" ")

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.casefold()
        if tag_name == "a" and self._anchor_depth > 0:
            self._anchor_depth -= 1
            return

        if tag_name in ("b", "strong") and self._bold_depth > 0:
            self._bold_depth -= 1

    def handle_data(self, data: str) -> None:
        self._append_text(data)

    def _store_anchor_url(
        self,
        attrs: List[Tuple[str, Optional[str]]],
    ) -> None:
        if self.url:
            return

        for name, value in attrs:
            if name.casefold() == "href" and value:
                self.url = value
                return

    def _store_image_path(
        self,
        attrs: List[Tuple[str, Optional[str]]],
    ) -> None:
        if self.image_path:
            return

        for name, value in attrs:
            if name.casefold() == "src" and value:
                self.image_path = value
                return

    def _append_text(self, data: str) -> None:
        text = " ".join(data.replace("\xa0", " ").split())
        if not text:
            return

        self.fragments.append(
            (text, self._anchor_depth > 0 or self._bold_depth > 0)
        )


class NewsBannerButton(ShiningButton):
    """Flat news banner button with rich text and subtle shimmer."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        self._banner_url = ""
        self._banner_display_html = ""
        self._banner_plain_text = ""
        self._banner_image_path = ""

        super().__init__("", parent)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumWidth(0)
        self.setMinimumHeight(NEWS_BANNER_MINIMUM_HEIGHT)
        self.setMaximumHeight(QT_WIDGET_MAX_SIZE)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        self._icon_label = QLabel(self)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._icon_label.setFixedSize(
            NEWS_BANNER_ICON_SIZE,
            NEWS_BANNER_ICON_SIZE,
        )
        self._icon_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self._icon_label.setVisible(False)

        self._text_label = QLabel(self)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._text_label.setTextFormat(Qt.TextFormat.RichText)
        self._text_label.setWordWrap(False)
        self._text_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        self._content_layout = QHBoxLayout(self)
        self._content_layout.setContentsMargins(
            NEWS_BANNER_PADDING_HORIZONTAL,
            NEWS_BANNER_PADDING_VERTICAL,
            NEWS_BANNER_PADDING_HORIZONTAL,
            NEWS_BANNER_PADDING_VERTICAL,
        )
        self._content_layout.setSpacing(0)
        self._content_layout.addStretch()
        self._content_layout.addWidget(
            self._icon_label,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        self._content_layout.addWidget(
            self._text_label,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        self._content_layout.addStretch()

        self.clicked.connect(self._open_banner_link)

    def set_banner_html(self, html: str) -> None:
        parser = NewsBannerHtmlParser()
        parser.feed(html)
        parser.close()

        self._banner_url = parser.url
        self._banner_display_html = parser.display_html
        self._banner_plain_text = parser.plain_text
        self._banner_image_path = parser.image_path
        self._text_label.setText(self._banner_display_html)
        self._update_banner_icon()
        self.setMinimumSize(self.minimumSizeHint())
        self.setToolTip(self._banner_plain_text)
        self.setEnabled(bool(self._banner_url))
        self.updateGeometry()
        self.update()

    def hasHeightForWidth(self) -> bool:
        return False

    def heightForWidth(self, width: int) -> int:
        del width
        return self._button_height_hint()

    def sizeHint(self) -> QSize:
        return QSize(
            max(self.width(), self._button_width_hint()),
            self._button_height_hint(),
        )

    def minimumSizeHint(self) -> QSize:
        return QSize(
            self._button_width_hint(),
            self._button_height_hint(),
        )

    def paintEvent(self, event) -> None:
        super(ShiningButton, self).paintEvent(event)
        self._paint_subtle_shimmer()

    def _normal_state(self) -> ButtonVisualState:
        return ButtonVisualState(
            background=self._overlay_color(
                NEWS_BANNER_NORMAL_BACKGROUND_ALPHA
            ),
            border=self._overlay_color(NEWS_BANNER_NORMAL_BORDER_ALPHA),
            text=self._text_color(),
        )

    def _hover_state(self) -> ButtonVisualState:
        return ButtonVisualState(
            background=self._overlay_color(NEWS_BANNER_HOVER_BACKGROUND_ALPHA),
            border=self._overlay_color(NEWS_BANNER_NORMAL_BORDER_ALPHA),
            text=self._text_color(),
        )

    def _pressed_state(self) -> ButtonVisualState:
        return ButtonVisualState(
            background=self._overlay_color(
                NEWS_BANNER_PRESSED_BACKGROUND_ALPHA
            ),
            border=self._overlay_color(NEWS_BANNER_NORMAL_BORDER_ALPHA),
            text=self._text_color(),
        )

    def _disabled_state(self) -> ButtonVisualState:
        return ButtonVisualState(
            background=self._overlay_color(10),
            border=self._overlay_color(28),
            text=self._text_color(),
        )

    def _border_radius(self) -> int:
        return NEWS_BANNER_BORDER_RADIUS

    def _open_banner_link(self) -> None:
        if not self._banner_url:
            return

        QDesktopServices.openUrl(QUrl(self._banner_url))

    def _overlay_color(self, alpha: int) -> QColor:
        color = QColor(self.palette().text().color())
        color.setAlpha(alpha)
        return color

    def _text_color(self) -> QColor:
        return QColor(self.palette().windowText().color())

    def _update_banner_icon(self) -> None:
        pixmap = QPixmap()
        if self._banner_image_path:
            pixmap = QPixmap(self._banner_image_path)

        has_icon = not pixmap.isNull()
        self._icon_label.setVisible(has_icon)
        self._text_label.setContentsMargins(
            NEWS_BANNER_ICON_TEXT_SPACING if has_icon else 0,
            0,
            0,
            0,
        )
        if not has_icon:
            self._icon_label.clear()
            return

        self._icon_label.setPixmap(
            pixmap.scaled(
                NEWS_BANNER_ICON_SIZE,
                NEWS_BANNER_ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _button_width_hint(self) -> int:
        return max(
            NEWS_BANNER_MINIMUM_WIDTH,
            self._content_width_hint()
            + NEWS_BANNER_PADDING_HORIZONTAL * 2
            + 2,
        )

    def _button_height_hint(self) -> int:
        return max(
            NEWS_BANNER_MINIMUM_HEIGHT,
            max(self._content_height_hint(), NEWS_BANNER_ICON_SIZE)
            + NEWS_BANNER_PADDING_VERTICAL * 2
            + 2,
        )

    def _content_width_hint(self) -> int:
        if not hasattr(self, "_text_label"):
            return 0

        content_width = self._text_label.sizeHint().width()
        if self._icon_label.isVisible():
            content_width += NEWS_BANNER_ICON_SIZE
            content_width += NEWS_BANNER_ICON_TEXT_SPACING

        return content_width

    def _content_height_hint(self) -> int:
        if not hasattr(self, "_text_label"):
            return 0

        return self._text_label.sizeHint().height()

    def _paint_subtle_shimmer(self) -> None:
        if not self.isEnabled() or self._shimmer_progress <= 0.0:
            return

        rect = self.rect().adjusted(1, 1, -1, -1)
        if rect.isEmpty():
            return

        band_width = max(NEWS_BANNER_SHIMMER_BAND_MIN_WIDTH, rect.width() // 4)
        center_x = rect.left() + rect.width() * self._shimmer_progress
        highlight = QColor(self._current_state.text)
        highlight.setAlpha(NEWS_BANNER_SHIMMER_ALPHA)
        transparent = QColor(highlight)
        transparent.setAlpha(0)

        gradient = QLinearGradient(
            center_x - band_width,
            rect.top(),
            center_x + band_width,
            rect.bottom(),
        )
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.5, highlight)
        gradient.setColorAt(1.0, transparent)

        painter = QPainter(self)
        painter.fillRect(rect, gradient)
        painter.end()


class Geoservice:
    """
    Represents QMS geospatial service entry.
    """

    def __init__(
        self, attributes: Dict[str, Any], image_ba: QByteArray
    ) -> None:
        """
        Initialize a Geoservice instance.

        :param attributes: Dictionary containing the geoservice metadata.
        :param image_ba: Binary image data associated with the service.
        :return: None
        """
        self.attributes = attributes
        self.image_ba = image_ba

    def is_valid(self) -> bool:
        """
        Check if the geoservice is valid.

        :return: True if valid, otherwise False.
        :rtype: bool
        """
        return self.attributes.get("id") is not None

    @property
    def id(self) -> int:
        """
        :return: The unique identifier of the geoservice.
        :rtype: int
        """
        return self.attributes.get("id")  # type: ignore

    def save_self(self, settings: QgsSettings) -> None:
        """
        Save this geoservice data into the provided settings group.

        :param settings: The settings group to store data into.
        :type settings: QgsSettings
        :return: None
        :rtype: None
        """
        settings.setValue(f"{self.id}/json", str(self.attributes))
        settings.setValue(f"{self.id}/image", self.image_ba)

    def load_self(self, _id: int, settings: QgsSettings) -> None:
        """
        Load this geoservice's data from the provided settings group.

        :param id: Identifier of the geoservice.
        :type id: int
        :param settings: The settings group to read data from.
        :type settings: QgsSettings
        :return: None
        :rtype: None
        """
        service_json = settings.value(f"{self.id}/json", None)
        self.attributes = ast.literal_eval(service_json)
        self.image_ba = settings.value(f"{self.id}/image", type=QByteArray)


@singleton
class CachedServices:
    def __init__(self):
        self.geoservices = []
        self.load_last_used_services()

    def load_last_used_services(self) -> None:
        """Load last used services from settings."""
        self.geoservices = []
        settings = QmsSettings()
        for geoservice, image_ba in settings.last_used_services:
            geoservice = Geoservice(geoservice, image_ba)
            if geoservice.is_valid():
                self.geoservices.append(geoservice)

    def add_service(
        self, geoservice: Dict[str, Any], image_ba: QByteArray
    ) -> None:
        """Add a service to the cache and persist it.

        :param geoservice: Dictionary containing metadata about the geospatial service.
        :type geoservice: Dict[str, Any]
        :param image_ba: Binary data used as the service icon image.
        :type image_ba: QByteArray

        :return: None
        :rtype: None
        """
        new_gs = Geoservice(geoservice, image_ba)
        geoservices4store = [new_gs]

        for gs in self.geoservices:
            if gs.id == new_gs.id:
                continue
            geoservices4store.append(gs)

        self.geoservices = geoservices4store[0:5]

        settings = QmsSettings()
        settings.last_used_services = self.geoservices

    def remove_service(self, service_id: int) -> None:
        """
        Remove a cached geoservice by its ID.

        :param service_id: Unique identifier of the geoservice to remove.
        :type service_id: int

        :return: None
        :rtype: None
        """
        self.geoservices = [
            geoservice
            for geoservice in self.geoservices
            if geoservice.id != service_id
        ]

        settings = QmsSettings()
        settings.last_used_services = self.geoservices

    def clear(self) -> None:
        """Clear cached geoservices and persist the empty list."""
        self.geoservices = []
        settings = QmsSettings()
        settings.last_used_services = self.geoservices

    def get_cached_services(self):
        return [
            (geoservice.attributes, geoservice.image_ba)
            for geoservice in self.geoservices
        ]


@singleton
class FavoriteServices:
    def __init__(self):
        self.geoservices = []
        self.load_favorite_services()

    def load_favorite_services(self) -> None:
        """Load favorite services from settings."""
        self.geoservices = []
        settings = QmsSettings()
        for geoservice, image_ba in settings.favorite_services:
            favorite_service = Geoservice(geoservice, image_ba)
            if favorite_service.is_valid():
                self.geoservices.append(favorite_service)

    def add_service(
        self, geoservice: Dict[str, Any], image_ba: QByteArray
    ) -> None:
        favorite_service = Geoservice(geoservice, image_ba)
        favorites = [
            stored_service
            for stored_service in self.geoservices
            if stored_service.id != favorite_service.id
        ]
        favorites.append(favorite_service)
        self.geoservices = favorites
        QmsSettings().favorite_services = self.geoservices

    def remove_service(self, service_id: int) -> None:
        self.geoservices = [
            geoservice
            for geoservice in self.geoservices
            if geoservice.id != service_id
        ]
        QmsSettings().favorite_services = self.geoservices

    def contains(self, service_id: Optional[int]) -> bool:
        if service_id is None:
            return False

        return any(
            geoservice.id == service_id for geoservice in self.geoservices
        )

    def get_favorite_services(self) -> List[Tuple[Dict[str, Any], QByteArray]]:
        return [
            (geoservice.attributes, geoservice.image_ba)
            for geoservice in self.geoservices
        ]

    def get_sorted_favorite_services(
        self,
    ) -> List[Tuple[Dict[str, Any], QByteArray]]:
        return sorted(
            self.get_favorite_services(),
            key=lambda item: str(item[0].get("name", "")).casefold(),
        )


FORM_CLASS, _ = uic.loadUiType(
    path.join(path.dirname(__file__), "qms_service_toolbox.ui")
)


class QmsServiceToolbox(QgsDockWidget, FORM_CLASS):
    """Dock widget for searching and selecting map services."""

    def __init__(self, iface: QgisInterface) -> None:
        """Initialize the search panel.

        :param iface: QGIS application interface.
        """
        QgsDockWidget.__init__(self, iface.mainWindow())
        self.setupUi(self)
        self.newsFrame.setVisible(False)

        self.iface = iface
        self.search_threads = None  # []
        self.extent_renderer = RubberBandResultRenderer()
        self._service_list_mode = self._saved_service_list_mode()
        self._data_sources_catalog = DataSourcesCatalog()

        self.favorites_menu = QMenu(self)
        self.contributed_services_menu = QMenu(self)
        self.main_menu = QMenu(self)
        self.lstSearchResult.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.lstSearchResult.viewport().installEventFilter(self)
        self._setup_news_banner()

        if hasattr(self.txtSearch, "setPlaceholderText"):
            self.txtSearch.setPlaceholderText(self.tr("Search string..."))

        self._setup_search_controls()

        self.delay_timer = QTimer(self)
        self.delay_timer.setSingleShot(True)
        self.delay_timer.setInterval(250)

        self.delay_timer.timeout.connect(self.start_search)
        self.txtSearch.textChanged.connect(self.delay_timer.start)
        self.btnFilterByExtent.toggled.connect(self.toggle_filter_button)
        self.one_process_work = QMutex()

        self.add_service_list_items()

        self.show_news()

    def eventFilter(self, watched, event) -> bool:
        if (
            watched == self.lstSearchResult.viewport()
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            event_position = event.pos()
            if hasattr(event, "position"):
                event_position = event.position().toPoint()

            item_index = self.lstSearchResult.indexAt(event_position)
            if not item_index.isValid():
                self.lstSearchResult.clearSelection()
                self.lstSearchResult.setCurrentItem(None)

        return super().eventFilter(watched, event)

    def _setup_search_controls(self) -> None:
        """Create controls displayed alongside the service search field."""
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(SEARCH_LAYOUT_SPACING)

        search_index = self.verticalLayout_2.indexOf(self.txtSearch)
        self.verticalLayout_2.removeWidget(self.txtSearch)

        search_layout.addWidget(self.txtSearch)
        search_height = self.txtSearch.sizeHint().height()
        self._setup_contributed_services_button(search_layout, search_height)
        self._setup_favorites_button(search_layout, search_height)
        self._setup_main_menu_button(search_layout, search_height)

        self.verticalLayout_2.insertLayout(search_index, search_layout)
        self.contributed_services_menu.aboutToShow.connect(
            self._populate_contributed_services_menu
        )
        self.favorites_menu.aboutToShow.connect(self._refresh_favorites_menu)
        self.main_menu.aboutToShow.connect(self._refresh_main_menu)
        self._refresh_favorites_menu()
        self._refresh_main_menu()

    def _setup_contributed_services_button(
        self,
        search_layout: QHBoxLayout,
        search_height: int,
    ) -> None:
        """Create the contributed-services menu button.

        :param search_layout: Layout receiving the button.
        :param search_height: Height shared by all search controls.
        """
        self.contributed_services_button = QToolButton(self)
        self.contributed_services_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.contributed_services_button.setToolTip(
            self.tr("Browse contributed and user services")
        )
        self.contributed_services_button.setMenu(
            self.contributed_services_menu
        )
        self.contributed_services_button.setIcon(
            material_icon(
                "layers",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            )
        )
        self.contributed_services_button.setFixedSize(
            search_height,
            search_height,
        )
        self.contributed_services_button.setIconSize(
            QSize(TOOL_BUTTON_ICON_SIZE, TOOL_BUTTON_ICON_SIZE)
        )
        search_layout.addWidget(self.contributed_services_button)

    def _setup_favorites_button(
        self,
        search_layout: QHBoxLayout,
        search_height: int,
    ) -> None:
        """Create the favorites and recent-services menu button.

        :param search_layout: Layout receiving the button.
        :param search_height: Height shared by all search controls.
        """
        self.btnFavorites = QToolButton(self)
        self.btnFavorites.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.btnFavorites.setMenu(self.favorites_menu)
        self.btnFavorites.setStyleSheet(self._tool_button_style_sheet())

        self.btnFavorites.setFixedSize(search_height, search_height)
        self.btnFavorites.setIconSize(
            QSize(TOOL_BUTTON_ICON_SIZE, TOOL_BUTTON_ICON_SIZE)
        )
        search_layout.addWidget(self.btnFavorites)
        self._update_service_list_mode_button_icon()

    def _setup_main_menu_button(
        self,
        search_layout: QHBoxLayout,
        search_height: int,
    ) -> None:
        """Create the search panel's main menu button.

        :param search_layout: Layout receiving the button.
        :param search_height: Height shared by all search controls.
        """
        self.main_menu_button = QToolButton(self)
        self.main_menu_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.main_menu_button.setToolTip(self.tr("Menu"))
        self.main_menu_button.setMenu(self.main_menu)
        self.main_menu_button.setIcon(
            material_icon(
                "menu",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            )
        )
        self.main_menu_button.setFixedSize(search_height, search_height)
        self.main_menu_button.setIconSize(
            QSize(TOOL_BUTTON_ICON_SIZE, TOOL_BUTTON_ICON_SIZE)
        )
        self.main_menu_button.setStyleSheet(self._tool_button_style_sheet())
        search_layout.addWidget(self.main_menu_button)

    @pyqtSlot()
    def _populate_contributed_services_menu(self) -> None:
        """Build the contributed-services menu from the local catalog."""
        self.contributed_services_menu.clear()
        self._data_sources_catalog.reload()
        hidden_data_source_ids = QmsSettings().hidden_datasource_id_list
        groups = self._data_sources_catalog.grouped_services(
            DataSourceCategory.all,
            hidden_data_source_ids,
        )
        for group in groups:
            group_menu = self.contributed_services_menu.addMenu(
                QIcon(group.info.icon),
                group.info.alias,
            )
            for data_source in group.data_sources:
                action = group_menu.addAction(
                    QIcon(data_source.icon_path),
                    data_source.alias,
                )
                action.triggered.connect(
                    lambda _checked, source=data_source: (
                        add_data_source_to_map(source)
                    )
                )

    def _update_service_list_mode_button_icon(self) -> None:
        icon_name = "history"
        tooltip = self.tr("Recent")
        if self._service_list_mode == SERVICE_LIST_MODE_FAVORITES:
            icon_name = "star"
            tooltip = self.tr("Favorites")

        self.btnFavorites.setToolTip(tooltip)
        self.btnFavorites.setIcon(
            material_icon(
                icon_name,
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            )
        )

    def _saved_service_list_mode(self) -> str:
        service_list_mode = QmsSettings().start_screen_service_list_mode
        if service_list_mode in (
            SERVICE_LIST_MODE_FAVORITES,
            SERVICE_LIST_MODE_RECENT,
        ):
            return service_list_mode

        return SERVICE_LIST_MODE_RECENT

    def _tool_button_style_sheet(self) -> str:
        return (
            "QToolButton {"
            "background: transparent;"
            "border: 1px solid transparent;"
            f"border-radius: {TOOL_BUTTON_BORDER_RADIUS}px;"
            "padding: 0;"
            "}"
            "QToolButton:hover {"
            f"background-color: {UI_NEUTRAL_BACKGROUND_HOVER};"
            f"border: 1px solid {UI_NEUTRAL_BORDER_SOFT};"
            "}"
            "QToolButton:pressed {"
            f"background-color: {UI_NEUTRAL_BACKGROUND_PRESSED};"
            f"border: 1px solid {UI_NEUTRAL_BORDER};"
            "}"
            "QToolButton::menu-indicator {"
            "image: none;"
            "width: 0px;"
            "}"
        )

    def _setup_news_banner(self) -> None:
        news_layout = self.newsFrame.layout()
        if news_layout is not None:
            news_layout.setContentsMargins(
                NEWS_BANNER_MARGIN_HORIZONTAL,
                NEWS_BANNER_MARGIN_VERTICAL,
                NEWS_BANNER_MARGIN_HORIZONTAL,
                NEWS_BANNER_MARGIN_VERTICAL,
            )
            news_layout.setSpacing(0)

        self.newsFrame.setFrameShape(QFrame.Shape.NoFrame)
        self.newsFrame.setStyleSheet(
            "QFrame#newsFrame {background: transparent;border: none;}"
        )
        self.newsLabel.setVisible(False)

        self.news_banner_button = NewsBannerButton(self.newsFrame)
        if news_layout is not None:
            news_layout.addWidget(self.news_banner_button)

    def _refresh_main_menu(self) -> None:
        self.main_menu.clear()

        add_to_search_action = self.main_menu.addAction(
            material_icon(
                "publish",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Contribute a Service"),
        )
        add_to_search_action.setToolTip(
            self.tr("Submit a new map service to the QMS catalog")
        )
        add_to_search_action.triggered.connect(self._open_add_to_search)

        clear_recent_action = self.main_menu.addAction(
            material_icon(
                "mop",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Clear recent"),
        )
        clear_recent_action.setEnabled(
            len(CachedServices().get_cached_services()) > 0
        )
        clear_recent_action.triggered.connect(self._clear_recent_services)

        self.main_menu.addSeparator()

        settings_action = self.main_menu.addAction(
            material_icon(
                "settings",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Settings..."),
        )
        settings_action.triggered.connect(self._open_settings)

        about_action = self.main_menu.addAction(
            material_icon(
                "info",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("About plugin..."),
        )
        about_action.triggered.connect(self._open_about)

    def _open_add_to_search(self) -> None:
        plugin = QuickMapServicesInterface.instance()
        open_url = getattr(plugin, "openURL", None)
        if callable(open_url):
            open_url()

    def _clear_recent_services(self) -> None:
        CachedServices().clear()
        if not self._is_service_list_mode_visible():
            return

        self.refresh_last_used_services()

    def _open_settings(self) -> None:
        plugin = QuickMapServicesInterface.instance()
        show_settings_dialog = getattr(plugin, "show_settings_dialog", None)
        if callable(show_settings_dialog):
            show_settings_dialog()

    def _open_about(self) -> None:
        plugin = QuickMapServicesInterface.instance()
        info_dialog = getattr(plugin, "info_dlg", None)
        if info_dialog is not None:
            info_dialog.show()

    def _refresh_favorites_menu(self) -> None:
        self.favorites_menu.clear()

        favorites_action = self.favorites_menu.addAction(
            material_icon(
                "star",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Favorites"),
        )
        favorites_action.setCheckable(True)
        favorites_action.setChecked(
            self._service_list_mode == SERVICE_LIST_MODE_FAVORITES
        )
        favorites_action.triggered.connect(
            lambda: self._set_service_list_mode(SERVICE_LIST_MODE_FAVORITES)
        )

        recent_action = self.favorites_menu.addAction(
            material_icon(
                "history",
                color=UiPaletteHelper.muted_icon_color(self),
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Recent"),
        )
        recent_action.setCheckable(True)
        recent_action.setChecked(
            self._service_list_mode == SERVICE_LIST_MODE_RECENT
        )
        recent_action.triggered.connect(
            lambda: self._set_service_list_mode(SERVICE_LIST_MODE_RECENT)
        )

    def _set_service_list_mode(self, service_list_mode: str) -> None:
        if service_list_mode not in (
            SERVICE_LIST_MODE_FAVORITES,
            SERVICE_LIST_MODE_RECENT,
        ):
            return

        if self._service_list_mode != service_list_mode:
            self._service_list_mode = service_list_mode
            QmsSettings().start_screen_service_list_mode = service_list_mode
            self._update_service_list_mode_button_icon()

        self._show_service_list_mode()

    def _show_service_list_mode(self) -> None:
        if self.btnFilterByExtent.isChecked():
            self.btnFilterByExtent.setChecked(False)

        self.delay_timer.stop()
        if str(self.txtSearch.text()):
            self.txtSearch.blockSignals(True)
            self.txtSearch.clear()
            self.txtSearch.blockSignals(False)

        if self.search_threads is not None:
            self.stop_search_thread()

        self.lstSearchResult.clear()
        self.add_service_list_items()
        self.lstSearchResult.clearSelection()
        self.lstSearchResult.setCurrentItem(None)

    def _is_service_list_mode_visible(self) -> bool:
        return not self.btnFilterByExtent.isChecked() and not str(
            self.txtSearch.text()
        )

    def _refresh_favorite_indicators(self) -> None:
        favorites = FavoriteServices()
        for widget in self._result_item_widgets():
            widget.set_is_favorite(favorites.contains(widget.service_id))

    def _result_item_widgets(self) -> List["QmsSearchResultItemWidget"]:
        widgets = []
        for item_index in range(self.lstSearchResult.count()):
            item = self.lstSearchResult.item(item_index)
            widget = self.lstSearchResult.itemWidget(item)
            if isinstance(widget, QmsSearchResultItemWidget):
                widgets.append(widget)

        return widgets

    def _sync_result_item_layouts(self) -> None:
        widgets = self._result_item_widgets()
        compact_width_hint = max(
            (widget.expanded_width_hint for widget in widgets), default=0
        )
        for widget in widgets:
            widget.set_compact_width_hint(compact_width_hint)

    def _create_result_item(
        self,
        geoservice: Dict[str, Any],
        image_ba: QByteArray,
        is_recent: bool = False,
        remove_on_missing: bool = False,
    ) -> QListWidgetItem:
        custom_widget = QmsSearchResultItemWidget(
            geoservice,
            image_ba,
            extent_renderer=self.extent_renderer,
            is_recent=is_recent,
            is_favorite=FavoriteServices().contains(geoservice.get("id")),
        )
        custom_widget.favorite_toggled.connect(self._handle_favorite_toggled)
        custom_widget.remove_recent_requested.connect(
            self._handle_remove_recent_service
        )

        def handle_missing_service(service_id: int) -> None:
            self._handle_remove_not_found_service(
                service_id,
                remove_recent=remove_on_missing,
                remove_favorite=FavoriteServices().contains(service_id),
            )

        custom_widget.service_not_found.connect(handle_missing_service)

        custom_widget.service_unavailable.connect(
            self._handle_service_unavailable
        )
        custom_widget.service_added.connect(self._handle_service_added_to_map)

        new_item = QListWidgetItem(self.lstSearchResult)
        new_item.setSizeHint(
            QSize(
                custom_widget.minimumSizeHint().width(),
                custom_widget.sizeHint().height(),
            )
        )
        self.lstSearchResult.addItem(new_item)
        self.lstSearchResult.setItemWidget(new_item, custom_widget)
        custom_widget.bind_list_item(new_item)
        self._sync_result_item_layouts()
        return new_item

    def _add_favorite_to_map(
        self, geoservice: Dict[str, Any], image_ba: QByteArray
    ) -> None:
        add_geoservice_to_map(
            geoservice,
            image_ba,
            service_not_found_callback=lambda service_id: (
                self._handle_remove_not_found_service(
                    service_id,
                    remove_recent=False,
                    remove_favorite=True,
                )
            ),
            service_unavailable_callback=self._handle_service_unavailable,
            service_added_callback=self._handle_service_added_to_map,
        )

    def _handle_service_added_to_map(self) -> None:
        if self._service_list_mode != SERVICE_LIST_MODE_RECENT:
            return

        if self.btnFilterByExtent.isChecked() or str(self.txtSearch.text()):
            return

        self.refresh_last_used_services()

    @pyqtSlot(object, QByteArray, bool)
    def _handle_favorite_toggled(
        self,
        geoservice: Dict[str, Any],
        image_ba: QByteArray,
        is_favorite: bool,
    ) -> None:
        favorites = FavoriteServices()
        service_id = geoservice.get("id")

        if is_favorite:
            favorites.add_service(geoservice, image_ba)
        elif isinstance(service_id, int):
            favorites.remove_service(service_id)

        self._refresh_favorites_menu()
        self._refresh_favorite_indicators()
        if (
            self._service_list_mode == SERVICE_LIST_MODE_FAVORITES
            and self._is_service_list_mode_visible()
        ):
            self.refresh_last_used_services()

    @pyqtSlot(int)
    def _handle_remove_recent_service(self, service_id: int) -> None:
        CachedServices().remove_service(service_id)
        self.refresh_last_used_services()

    def show_news(self):
        self.newsFrame.setVisible(False)

        short_locale = utils.qgis_locale(adapt=False)

        def make_utm(campaign: str, locale: str = short_locale) -> str:
            return "&".join(
                [
                    "utm_source=qgis_plugin",
                    "utm_medium=banner",
                    f"utm_campaign={campaign}",
                    f"utm_term={PACKAGE_NAME}",
                    f"utm_content={locale}",
                ]
            )

        utm = make_utm("constant")
        bf25_utm = make_utm("black-friday25")
        nextgis15_url = f"https://data.nextgis.com/?{make_utm('nextgis15')}"

        qms_nextgis15_news = QmsNews(
            {
                "ru": (
                    f'<a href="{nextgis15_url}">Нам 15 лет! '
                    "Дарим скидки 15% на все наборы данных</a><br>"
                    "С 8 по 15 июня – успейте заказать!"
                ),
                "en": (
                    f'<a href="{nextgis15_url}">NextGIS is 15! '
                    "And all our datasets are 15% off</a><br>"
                    "June 8th to June 15th – order now!"
                ),
                "fr": (
                    f'<a href="{nextgis15_url}">Nous fêtons nos '
                    "15 ans : profitez de 15 % de réduction !</a><br>"
                    "Sur tous nos jeux de données, seulement du 8 au 15 juin."
                ),
                "es": (
                    f'<a href="{nextgis15_url}">¡Cumplimos 15 años! '
                    "Disfruta de un 15 % de<br/>descuento en todos los "
                    "conjuntos de datos</a><br>"
                    "Del 8 al 15 de junio. ¡No te lo pierdas!"
                ),
            }
        )

        qms_black_friday_news = QmsNews(
            {
                "ru": f'<a href="https://data.nextgis.com/?{bf25_utm}">Свежие геоданные</a> для проекта. <b>Экономия 50%!</b>',
                "en": f'<a href="https://data.nextgis.com/?{bf25_utm}">Fresh geodata</a> for your project <b>(50% off!)</b>',
            }
        )
        qms_news = QmsNews(
            {
                "ru": f'<a href="https://data.nextgis.com/?{utm}">Скачайте геоданные</a> для проекта',
                "en": f'<a href="https://data.nextgis.com/?{utm}">Download geodata</a> for your project',
            }
        )
        if qms_black_friday_news is None and qms_news is None:
            return

        black_friday_start = datetime(
            year=2025, month=12, day=1, hour=6, minute=1, tzinfo=timezone.utc
        )
        black_friday_finish = datetime(
            year=2025, month=12, day=6, hour=5, minute=59, tzinfo=timezone.utc
        )
        nextgis15_start = datetime(
            year=2026, month=6, day=8, hour=6, minute=0, tzinfo=timezone.utc
        )
        nextgis15_finish = datetime(
            year=2026, month=6, day=16, hour=5, minute=59, tzinfo=timezone.utc
        )
        nextgis15_news = News(
            qms_nextgis15_news,
            date_start=nextgis15_start,
            date_finish=nextgis15_finish,
            icon="anniversary.svg",
            layout=NewsLayout.ANNIVERSARY,
        )
        black_friday_news = News(
            qms_black_friday_news,
            date_start=black_friday_start,
            date_finish=black_friday_finish,
            icon="fire.png",
        )
        ordinary_news = News(qms_news)

        self.newsFrame.setVisible(False)
        for news in [nextgis15_news, black_friday_news, ordinary_news]:
            if news.is_time_to_show():
                self.news_banner_button.set_banner_html(news.html)
                self.newsFrame.setVisible(True)
                break

    def toggle_filter_button(self, checked):
        self.txtSearch.setDisabled(checked)
        if checked:
            self.iface.mapCanvas().extentsChanged.connect(self.start_search)
            self.iface.mapCanvas().destinationCrsChanged.connect(
                self.start_search
            )
            self.start_search()
        else:
            self.iface.mapCanvas().extentsChanged.disconnect(self.start_search)
            self.iface.mapCanvas().destinationCrsChanged.disconnect(
                self.start_search
            )

    def stop_search_thread(self):
        self.search_threads.data_downloaded.disconnect()
        self.search_threads.search_finished.disconnect()
        self.search_threads.stop()
        self.search_threads.wait()
        self.search_threads = None

    @pyqtSlot()
    def refresh_last_used_services(self):
        """
        Refresh the list of last used geoservices.

        This method clears the current search result list and adds the
        last used geoservices again. It is intended to be called after
        a geoservice is removed from the recent list.
        """
        self.lstSearchResult.clear()
        self.add_service_list_items()

    @pyqtSlot()
    def start_search(self) -> None:
        """
        Start a QuickMapServices search process based on user input or current map extent.

        :return: None
        :rtype: None
        """
        search_text = None
        geom_filter = None
        min_search_text_len = 3

        if not self.btnFilterByExtent.isChecked():
            # text search
            search_text = str(self.txtSearch.text())

            if not search_text:
                self.lstSearchResult.clear()
                self.add_service_list_items()
                return

            if len(search_text) < min_search_text_len:
                if self.search_threads:
                    self.stop_search_thread()
                self.lstSearchResult.clear()
                self.lstSearchResult.insertItem(
                    0, self.tr("Need at least 3 symbols to start searching...")
                )
                return
        else:
            # extent filter
            extent = self.iface.mapCanvas().extent()
            map_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
            if map_crs.postgisSrid() != 4326:
                dest_crs = QgsCoordinateReferenceSystem.fromEpsgId(
                    4326
                )  # WGS 84
                xform = QgsCoordinateTransform(
                    map_crs, dest_crs, QgsProject.instance()
                )
                extent = xform.transform(extent)
            geom_filter = extent.asWktPolygon()

        if self.search_threads:
            self.stop_search_thread()
            self.lstSearchResult.clear()

        searcher = SearchThread(
            search_text,
            self.one_process_work,
            parent=self.iface.mainWindow(),
            geom_filter=geom_filter,
        )
        searcher.data_downloaded.connect(self.show_result)
        searcher.error_occurred.connect(self.show_error)
        searcher.search_started.connect(self.search_started_process)
        searcher.search_finished.connect(self.search_finished_progress)
        self.search_threads = searcher
        searcher.start()

    def add_service_list_items(self) -> None:
        if self._service_list_mode == SERVICE_LIST_MODE_FAVORITES:
            self.add_favorite_services()
            return

        self.add_last_used_services()

    def _add_header_item(self, text: str) -> None:
        header_item = QListWidgetItem(text)
        header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.lstSearchResult.addItem(header_item)

    def _add_empty_item(self, text: str) -> None:
        empty_item = QListWidgetItem(text)
        empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.lstSearchResult.addItem(empty_item)

    def add_favorite_services(self) -> None:
        """
        Populate the search result list with favorite geoservices.

        :return: None
        :rtype: None
        """
        services = FavoriteServices().get_sorted_favorite_services()
        if len(services) == 0:
            self._add_empty_item(self.tr("No favorites"))
            return

        self._add_header_item(self.tr("Favorites:"))
        for attributes, image_qByteArray in services:
            self._create_result_item(
                attributes,
                image_qByteArray,
                is_recent=False,
                remove_on_missing=False,
            )

    def add_last_used_services(self) -> None:
        """
        Populate the search result list with recently used geoservices.

        :return: None
        :rtype: None
        """
        services = CachedServices().get_cached_services()
        if len(services) == 0:
            self._add_empty_item(self.tr("No recent services"))
            return

        self._add_header_item(self.tr("Last used:"))
        # l = QLabel(self.tr("Last used:"))
        # l.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # self.lSearchResult.addWidget(l)

        for attributes, image_qByteArray in services:
            self._create_result_item(
                attributes,
                image_qByteArray,
                is_recent=True,
                remove_on_missing=True,
            )
            # self.lSearchResult.addWidget(custom_widget)

        # w = QWidget()
        # w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.lSearchResult.addWidget(w)

    def search_started_process(self):
        self.lstSearchResult.clear()
        self.lstSearchResult.insertItem(0, self.tr("Searching..."))

    def search_finished_progress(self):
        self.lstSearchResult.takeItem(0)
        if self.lstSearchResult.count() == 0:
            new_widget = QLabel()
            new_widget.setTextFormat(Qt.TextFormat.RichText)
            new_widget.setOpenExternalLinks(True)
            new_widget.setWordWrap(True)
            new_widget.setText(
                "<div align='center'> <strong>{}</strong> </div><div align='center' style='margin-top: 3px'> {} </div>".format(
                    self.tr("No results."),
                    self.tr(
                        "You can add a service to become searchable. Start <a href='{}'>here</a>."
                    ).format("https://qms.nextgis.com/create"),
                )
            )
            new_item = QListWidgetItem(self.lstSearchResult)
            new_item.setSizeHint(new_widget.sizeHint())
            self.lstSearchResult.addItem(new_item)
            self.lstSearchResult.setItemWidget(new_item, new_widget)

    def show_result(
        self, geoservice: Optional[Dict[str, Any]], image_ba: QByteArray
    ) -> None:
        """
        Display a search result item in the result list.

        :param geoservice: The geoservice attributes dictionary, or None if no result.
        :type geoservice: Optional[Dict[str, Any]]
        :param image_ba: The image data for the service icon.
        :type image_ba: QByteArray

        :return: None
        :rtype: None
        """
        if geoservice:
            self._create_result_item(geoservice, image_ba)

        else:
            new_item = QListWidgetItem()
            new_item.setText(self.tr("No results!"))
            new_item.setData(Qt.ItemDataRole.UserRole, None)
            self.lstSearchResult.addItem(new_item)
        self.lstSearchResult.update()

    def show_error(self, error_text):
        self.lstSearchResult.clear()
        new_widget = QLabel()
        new_widget.setTextFormat(Qt.TextFormat.RichText)
        new_widget.setOpenExternalLinks(True)
        new_widget.setWordWrap(True)
        new_widget.setText(
            "<div align='center'> <strong>{}</strong> </div><div align='center' style='margin-top: 3px'> {} </div>".format(
                self.tr("Error"), error_text
            )
        )
        new_item = QListWidgetItem(self.lstSearchResult)
        new_item.setSizeHint(new_widget.sizeHint())
        self.lstSearchResult.addItem(new_item)
        self.lstSearchResult.setItemWidget(new_item, new_widget)

    def _handle_remove_not_found_service(
        self,
        service_id: int,
        remove_recent: bool,
        remove_favorite: bool,
    ) -> None:
        if remove_recent and remove_favorite:
            message = self.tr(
                "The service no longer exists and has been removed from the recent list and favorites."
            )
        elif remove_recent:
            message = self.tr(
                "The service no longer exists and has been removed from the recent list."
            )
        elif remove_favorite:
            message = self.tr(
                "The service no longer exists and has been removed from favorites."
            )
        else:
            message = self.tr("The requested service could not be found.")

        QMessageBox.warning(self, self.tr("Service not found"), message)

        if remove_recent:
            CachedServices().remove_service(service_id)
            self.refresh_last_used_services()

        if remove_favorite:
            FavoriteServices().remove_service(service_id)
            self._refresh_favorites_menu()
            self._refresh_favorite_indicators()

    @pyqtSlot(str)
    def _handle_service_unavailable(self, message: str) -> None:
        """
        Handle the event when a service is temporarily unavailable.

        :param message: The error message describing why the service is unavailable.
        :type message: str
        :return: None
        :rtype: None
        """
        msg = self.tr(
            "The service is currently unavailable due to network or server issues. "
            "Please try again later.\nError: {error_msg}"
        ).format(error_msg=message)
        QMessageBox.warning(
            self,
            self.tr("Service is unavailable"),
            msg,
        )


class QmsLinkLabel(QLabel):
    """QLabel-based link with explicit hover styling."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._link_url = ""
        self._link_text = ""
        self._is_hovered = False

        self.setTextFormat(Qt.TextFormat.RichText)
        self.setOpenExternalLinks(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )

    def set_link(self, link_url: str, link_text: str) -> None:
        self._link_url = link_url
        self._link_text = link_text
        self.setProperty("link_url", link_url)
        self.setProperty("link_text", link_text)
        self._update_text()

    def enterEvent(self, event) -> None:
        self._set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered(False)
        super().leaveEvent(event)

    def _set_hovered(self, is_hovered: bool) -> None:
        if self._is_hovered == is_hovered:
            return

        self._is_hovered = is_hovered
        self._update_text()

    def _update_text(self) -> None:
        if not self._link_url:
            self.setText("")
            return

        link_color = QColor(self.palette().link().color())
        if self._is_hovered:
            link_color = link_color.lighter(125)

        text_decoration = "underline" if self._is_hovered else "none"
        escaped_url = escape(self._link_url, quote=True)
        escaped_text = escape(self._link_text)
        self.setText(
            f'<a href="{escaped_url}" style="'
            f"color: {link_color.name()}; "
            f"text-decoration: {text_decoration};"
            f'">{escaped_text}</a>'
        )


class QmsSearchResultItemWidget(QWidget):
    """
    A custom QWidget representing a single search result item
    in the QuickMapServices (QMS) plugin.
    """

    service_not_found = pyqtSignal(int)
    service_unavailable = pyqtSignal(str)
    service_added = pyqtSignal()
    favorite_toggled = pyqtSignal(object, QByteArray, bool)
    remove_recent_requested = pyqtSignal(int)

    def __init__(
        self,
        geoservice: Dict[str, Any],
        image_ba: QByteArray,
        parent: Optional[QWidget] = None,
        extent_renderer: Optional["RubberBandResultRenderer"] = None,
        is_recent: bool = False,
        is_favorite: bool = False,
    ) -> None:
        """
        Initialize the QMS search result item widget.

        :param geoservice: Dictionary containing metadata about the geospatial service.
        :type geoservice: Dict[str, Any]
        :param image_ba: Binary data used as the service icon image.
        :type image_ba: QByteArray
        :param parent: Parent widget of this UI element.
        :type parent: Optional[QWidget]
        :param extent_renderer: Optional renderer used to visualize the service extent.
        :type extent_renderer: Optional[RubberBandResultRenderer]

        :return: None
        :rtype: None
        """
        super().__init__(parent)

        self.extent_renderer = extent_renderer
        self.is_recent = is_recent
        self.is_favorite = is_favorite
        self._list_item = None
        self._is_updating_layout = False
        self._is_compact = False
        self._compact_width_hint = 0

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(
            SERVICE_RESULT_CARD_OUTER_MARGIN,
            SERVICE_RESULT_CARD_OUTER_MARGIN,
            SERVICE_RESULT_CARD_OUTER_MARGIN,
            SERVICE_RESULT_CARD_OUTER_MARGIN,
        )
        self.outer_layout.setSpacing(0)
        self.setLayout(self.outer_layout)

        self.card = QFrame(self)
        self.card.setObjectName("serviceCard")
        self.card.setFrameShape(QFrame.Shape.StyledPanel)
        self.card.setFrameShadow(QFrame.Shadow.Raised)
        add_button_color = UiPaletteHelper.muted_icon_color(self)
        add_button_active_color = UiPaletteHelper.active_icon_color(self)
        self.card.setStyleSheet(
            "QFrame#serviceCard {"
            f"border: 1px solid {UI_NEUTRAL_BORDER_SOFT};"
            f"border-radius: {SERVICE_RESULT_CARD_BORDER_RADIUS}px;"
            f"background-color: {UI_NEUTRAL_BACKGROUND_SOFT};"
            "}"
            "QLabel#serviceNameLabel { font-weight: 600; }"
            "QLabel#serviceTypeBadge {"
            f"padding: {SERVICE_RESULT_BADGE_PADDING_VERTICAL}px "
            f"{SERVICE_RESULT_BADGE_PADDING_HORIZONTAL}px;"
            f"border-radius: {SERVICE_RESULT_CONTROL_BORDER_RADIUS}px;"
            f"background-color: {UI_NEUTRAL_BACKGROUND};"
            f"border: 1px solid {UI_NEUTRAL_BORDER_SOFT};"
            "color: palette(text);"
            "font-weight: 500;"
            "}"
            "QToolButton#serviceAddButton {"
            f"padding-left: {SERVICE_RESULT_ADD_PADDING_HORIZONTAL}px;"
            f"padding-right: {SERVICE_RESULT_ADD_PADDING_HORIZONTAL}px;"
            f"padding-top: {SERVICE_RESULT_ADD_PADDING_VERTICAL}px;"
            f"padding-bottom: {SERVICE_RESULT_ADD_PADDING_VERTICAL}px;"
            "background: transparent;"
            "border: 1px solid transparent;"
            f"color: {add_button_color};"
            f"border-radius: {SERVICE_RESULT_CONTROL_BORDER_RADIUS}px;"
            "}"
            "QToolButton#serviceAddButton:hover {"
            f"background-color: {UI_NEUTRAL_BACKGROUND_HOVER};"
            f"border: 1px solid {UI_NEUTRAL_BORDER_SOFT};"
            f"color: {add_button_active_color};"
            "}"
            "QToolButton#serviceAddButton:pressed {"
            f"background-color: {UI_NEUTRAL_BACKGROUND_PRESSED};"
            f"border: 1px solid {UI_NEUTRAL_BORDER};"
            f"color: {add_button_active_color};"
            "}"
        )
        self.outer_layout.addWidget(self.card)

        self.layout = QHBoxLayout(self.card)
        self.layout.setContentsMargins(
            SERVICE_RESULT_CARD_MARGIN_HORIZONTAL,
            SERVICE_RESULT_CARD_MARGIN_VERTICAL,
            SERVICE_RESULT_CARD_MARGIN_HORIZONTAL,
            SERVICE_RESULT_CARD_MARGIN_VERTICAL,
        )
        self.layout.setSpacing(SERVICE_RESULT_CARD_MAIN_SPACING)

        self.service_icon = QLabel(self)
        self.service_icon.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.service_icon.setFixedSize(
            SERVICE_RESULT_ICON_SIZE, SERVICE_RESULT_ICON_SIZE
        )
        self.service_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qimg = QImage.fromData(image_ba)
        pixmap = QPixmap.fromImage(qimg)
        if not pixmap.isNull():
            self.service_icon.setPixmap(
                pixmap.scaled(
                    SERVICE_RESULT_ICON_PIXMAP_SIZE,
                    SERVICE_RESULT_ICON_PIXMAP_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.layout.addWidget(self.service_icon)
        self.layout.setAlignment(
            self.service_icon, Qt.AlignmentFlag.AlignVCenter
        )

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(SERVICE_RESULT_CONTENT_SPACING)
        self.layout.addLayout(self.content_layout)
        self.layout.setStretch(1, 1)

        self.service_name_layout = QHBoxLayout()
        self.service_name_layout.setContentsMargins(0, 0, 0, 0)
        self.service_name_layout.setSpacing(SERVICE_RESULT_NAME_SPACING)

        self.favorite_indicator = QLabel(self)
        self.favorite_indicator.setPixmap(
            QgsApplication.getThemeIcon("mIconFavorites.svg").pixmap(
                SERVICE_RESULT_FAVORITE_ICON_SIZE,
                SERVICE_RESULT_FAVORITE_ICON_SIZE,
            )
        )
        self.favorite_indicator.setFixedSize(
            SERVICE_RESULT_FAVORITE_ICON_SIZE,
            SERVICE_RESULT_FAVORITE_ICON_SIZE,
        )
        self.favorite_indicator.setVisible(self.is_favorite)
        self.service_name_layout.addWidget(self.favorite_indicator)

        self.service_name = QLabel(self)
        self.service_name.setObjectName("serviceNameLabel")
        self.service_name.setTextFormat(Qt.TextFormat.PlainText)
        self.service_name.setWordWrap(False)
        self.service_name.setMinimumWidth(0)
        self.service_name.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.service_name.setToolTip(str(geoservice.get("name", "")))
        self.service_name_layout.addWidget(self.service_name)
        self.service_name_layout.setStretch(1, 1)
        self.content_layout.addLayout(self.service_name_layout)

        self.service_meta_layout = QHBoxLayout()
        self.service_meta_layout.setContentsMargins(0, 0, 0, 0)
        self.service_meta_layout.setSpacing(SERVICE_RESULT_META_SPACING)

        self.service_type_badge = QLabel(self)
        self.service_type_badge.setObjectName("serviceTypeBadge")
        self.service_type_badge.setText(geoservice.get("type", "").upper())
        self.service_type_badge.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.service_meta_layout.addWidget(self.service_type_badge)

        self.service_deteils = self._create_link_label(
            Client().geoservice_info_url(geoservice.get("id", "")),
            self.tr("details"),
        )
        self.service_deteils.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.service_meta_layout.addWidget(self.service_deteils)

        self.service_report_full_text = self.tr("report a problem")
        self.service_report_short_text = self.tr("report")
        self.service_report = self._create_link_label(
            Client().geoservice_report_url(geoservice.get("id", "")),
            self.service_report_full_text,
        )
        self.service_report.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.service_meta_layout.addWidget(self.service_report)
        self.service_meta_layout.addStretch()
        self.content_layout.addLayout(self.service_meta_layout)

        self.addButton = QToolButton()
        self.addButton.setObjectName("serviceAddButton")
        self.addButton.setText(self.tr("Add"))
        self.addButton.setToolTip(self.tr("Add"))
        self.addButton.setIcon(
            material_icon(
                "add",
                color=add_button_color,
                size=SERVICE_RESULT_ADD_ICON_SIZE,
            )
        )
        self.addButton.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.addButton.setAutoRaise(True)
        self.addButton.setIconSize(
            QSize(SERVICE_RESULT_ADD_ICON_SIZE, SERVICE_RESULT_ADD_ICON_SIZE)
        )
        self.addButton.setMinimumHeight(SERVICE_RESULT_ADD_COMPACT_SIZE)
        self.addButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.addButton.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.addButton.installEventFilter(self)
        self.addButton.clicked.connect(self.addToMap)

        self.action_layout = QVBoxLayout()
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(0)
        self.action_layout.addStretch()
        self.action_layout.addWidget(
            self.addButton, 0, Qt.AlignmentFlag.AlignCenter
        )
        self.action_layout.addStretch()
        self.layout.addLayout(self.action_layout)

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )

        self.geoservice = geoservice
        self.image_ba = image_ba
        self.service_name_full_text = str(geoservice.get("name", ""))
        self.add_button_full_text = self.tr("Add")
        self._expanded_width_hint = self.sizeHint().width()
        self.service_name.setText(self.service_name_full_text)
        self._setup_context_menu_targets()

    @property
    def service_id(self) -> Optional[int]:
        return self.geoservice.get("id")

    def minimumSizeHint(self) -> QSize:
        size_hint = super().minimumSizeHint()
        minimum_width = self._minimum_width()
        if minimum_width <= 0:
            return QSize(0, size_hint.height())

        return QSize(minimum_width, size_hint.height())

    @property
    def expanded_width_hint(self) -> int:
        return self._expanded_width_hint

    def set_is_favorite(self, is_favorite: bool) -> None:
        self.is_favorite = is_favorite
        self.favorite_indicator.setVisible(is_favorite)

    def set_compact_width_hint(self, compact_width_hint: int) -> None:
        if self._compact_width_hint == compact_width_hint:
            return

        self._compact_width_hint = compact_width_hint
        self._update_layout_state()

    def bind_list_item(self, list_item: QListWidgetItem) -> None:
        self._list_item = list_item
        QTimer.singleShot(0, self._update_layout_state)

    def eventFilter(self, watched, event) -> bool:
        if watched == self.addButton:
            if event.type() == QEvent.Type.Enter:
                self._update_add_button_icon(is_hovered=True)
            elif event.type() == QEvent.Type.Leave:
                self._update_add_button_icon(is_hovered=False)

        return super().eventFilter(watched, event)

    def _update_layout_state(self) -> None:
        if self._is_updating_layout:
            return

        if self._list_item is not None and not self.isVisible():
            return

        self._is_updating_layout = True
        try:
            available_width = self._available_width()
            is_compact = (
                available_width > 0
                and available_width < self._effective_compact_width_hint()
            )
            self._set_compact_mode(is_compact)
            self._fix_meta_label_widths()
            self._update_minimum_width()
            self._activate_layouts()
            self._update_service_name_text()
            self._sync_list_item_size()
        finally:
            self._is_updating_layout = False

    def _available_width(self) -> int:
        if self._list_item is not None:
            list_widget = self._list_item.listWidget()
            if list_widget is not None:
                viewport_width = list_widget.viewport().width()
                if viewport_width > 0:
                    return viewport_width

        return self.width()

    def _effective_compact_width_hint(self) -> int:
        return max(self._compact_width_hint, self._expanded_width_hint)

    def _activate_layouts(self) -> None:
        self.outer_layout.activate()
        self.layout.activate()
        self.content_layout.activate()
        self.service_name_layout.activate()
        self.service_meta_layout.activate()

    def _fix_meta_label_widths(self) -> None:
        for label in (
            self.service_type_badge,
            self.service_deteils,
            self.service_report,
        ):
            label.setMinimumWidth(0)
            label.setMaximumWidth(QT_WIDGET_MAX_SIZE)
            label.updateGeometry()
            label.setFixedWidth(label.sizeHint().width())

    def _update_minimum_width(self) -> None:
        minimum_width = self._minimum_width()
        if minimum_width <= 0:
            return

        if self.minimumWidth() != minimum_width:
            self.setMinimumWidth(minimum_width)

    def _minimum_width(self) -> int:
        if not hasattr(self, "service_report"):
            return 0

        outer_margins = self.outer_layout.contentsMargins()
        card_margins = self.layout.contentsMargins()
        icon_width = self.service_icon.width()
        add_button_width = self.addButton.sizeHint().width()

        if self._is_compact:
            add_button_width = SERVICE_RESULT_ADD_COMPACT_SIZE

        horizontal_margins = (
            outer_margins.left()
            + outer_margins.right()
            + card_margins.left()
            + card_margins.right()
        )
        fixed_width = (
            horizontal_margins
            + icon_width
            + add_button_width
            + SERVICE_RESULT_CARD_MAIN_SPACING * 2
        )

        return fixed_width + self._meta_one_row_width()

    def _meta_one_row_width(self) -> int:
        return (
            self.service_type_badge.sizeHint().width()
            + self.service_deteils.sizeHint().width()
            + self.service_report.sizeHint().width()
            + SERVICE_RESULT_META_SPACING * 2
        )

    def _sync_list_item_size(self) -> None:
        if self._list_item is None:
            return

        size_hint = QSize(
            self.minimumSizeHint().width(), self.sizeHint().height()
        )
        if self._list_item.sizeHint() != size_hint:
            self._list_item.setSizeHint(size_hint)

    def _update_service_name_text(self) -> None:
        metrics = self.service_name.fontMetrics()
        available_width = max(
            self.service_name.width() - SERVICE_RESULT_NAME_ELIDE_PADDING,
            SERVICE_RESULT_NAME_MIN_ELIDE_WIDTH,
        )
        elided_text = metrics.elidedText(
            self.service_name_full_text,
            Qt.TextElideMode.ElideRight,
            available_width,
        )
        self.service_name.setText(elided_text)

    def _create_link_label(self, link_url: str, link_text: str) -> QLabel:
        label = QmsLinkLabel(self)
        self._update_link_label(label, link_text, link_url)
        return label

    def _update_link_label(
        self,
        label: QLabel,
        link_text: str,
        link_url: Optional[str] = None,
    ) -> None:
        current_link_url = link_url
        if current_link_url is None:
            current_link_url = str(label.property("link_url"))

        if isinstance(label, QmsLinkLabel):
            label.set_link(current_link_url, link_text)

    def _update_report_link_text(self, is_compact: bool) -> None:
        report_text = self.service_report_full_text
        if is_compact:
            report_text = self.service_report_short_text

        if self.service_report.property("link_text") == report_text:
            return

        self.service_report.setProperty("link_text", report_text)
        self._update_link_label(self.service_report, report_text)
        self.service_report.updateGeometry()

    def _set_compact_mode(self, is_compact: bool) -> None:
        if self._is_compact == is_compact:
            return

        self._is_compact = is_compact
        self._update_add_button_presentation(is_compact)
        self._update_report_link_text(is_compact)

    def _update_add_button_presentation(self, is_compact: bool) -> None:
        if is_compact:
            self.addButton.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonIconOnly
            )
            self.addButton.setText("")
            self.addButton.setMinimumSize(
                SERVICE_RESULT_ADD_COMPACT_SIZE,
                SERVICE_RESULT_ADD_COMPACT_SIZE,
            )
            self.addButton.setMaximumSize(
                SERVICE_RESULT_ADD_COMPACT_SIZE,
                SERVICE_RESULT_ADD_COMPACT_SIZE,
            )
        else:
            self.addButton.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            self.addButton.setText(self.add_button_full_text)
            self.addButton.setMinimumSize(0, SERVICE_RESULT_ADD_COMPACT_SIZE)
            self.addButton.setMaximumSize(
                QT_WIDGET_MAX_SIZE, QT_WIDGET_MAX_SIZE
            )

        self.addButton.updateGeometry()
        self.service_meta_layout.invalidate()
        self.content_layout.invalidate()
        self.layout.invalidate()
        self.outer_layout.invalidate()

    def _update_add_button_icon(self, is_hovered: bool) -> None:
        color = UiPaletteHelper.muted_icon_color(self)
        if is_hovered:
            color = UiPaletteHelper.active_icon_color(self)

        self.addButton.setIcon(
            material_icon(
                "add",
                color=color,
                size=SERVICE_RESULT_ADD_ICON_SIZE,
            )
        )

    def _setup_context_menu_targets(self) -> None:
        context_targets = [
            self,
            self.card,
            self.service_icon,
            self.favorite_indicator,
            self.service_name,
            self.service_type_badge,
            self.service_deteils,
            self.service_report,
            self.addButton,
        ]

        for widget in context_targets:
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda pos, current_widget=widget: self._show_context_menu(
                    current_widget.mapToGlobal(pos)
                )
            )

    def _open_label_link(self, label: QLabel) -> None:
        link_url = label.property("link_url")
        if not link_url:
            return

        QDesktopServices.openUrl(QUrl(str(link_url)))

    def _show_context_menu(self, global_pos) -> None:
        menu = QMenu(self)
        action_icon_color = UiPaletteHelper.muted_icon_color(self)

        add_action = menu.addAction(
            material_icon(
                "add",
                color=action_icon_color,
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Add to project"),
        )
        add_action.triggered.connect(self.addToMap)

        details_action = menu.addAction(
            material_icon(
                "info_20dp",
                color=action_icon_color,
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Details"),
        )
        details_action.triggered.connect(
            lambda: self._open_label_link(self.service_deteils)
        )

        report_action = menu.addAction(
            material_icon(
                "warning",
                color=action_icon_color,
                size=TOOL_BUTTON_ICON_SIZE,
            ),
            self.tr("Report a problem"),
        )
        report_action.triggered.connect(
            lambda: self._open_label_link(self.service_report)
        )

        menu.addSeparator()

        if self.is_favorite:
            favorite_action = menu.addAction(
                material_icon(
                    "star",
                    color=action_icon_color,
                    size=TOOL_BUTTON_ICON_SIZE,
                    fill=0,
                ),
                self.tr("Remove from favorites"),
            )
            favorite_action.triggered.connect(
                lambda: self.favorite_toggled.emit(
                    self.geoservice, self.image_ba, False
                )
            )
        else:
            favorite_action = menu.addAction(
                material_icon(
                    "star",
                    color=action_icon_color,
                    size=TOOL_BUTTON_ICON_SIZE,
                    fill=1,
                ),
                self.tr("Save to favorites"),
            )
            favorite_action.triggered.connect(
                lambda: self.favorite_toggled.emit(
                    self.geoservice, self.image_ba, True
                )
            )

        if self.is_recent:
            remove_recent_action = menu.addAction(
                material_icon(
                    "delete",
                    color=action_icon_color,
                    size=TOOL_BUTTON_ICON_SIZE,
                ),
                self.tr("Remove from recent"),
            )
            remove_recent_action.triggered.connect(
                lambda: self.remove_recent_requested.emit(self.service_id)
            )

        menu.exec(global_pos)

    @pyqtSlot()
    def addToMap(self) -> None:
        """
        Try to add the selected geoservice to the map.
        """
        add_geoservice_to_map(
            self.geoservice,
            self.image_ba,
            service_not_found_callback=self.service_not_found.emit,
            service_unavailable_callback=self.service_unavailable.emit,
            service_added_callback=self.service_added.emit,
        )

    def mouseDoubleClickEvent(self, event):
        self.addToMap()

    def enterEvent(self, event):
        extent = self.geoservice.get("extent", None)
        if self.extent_renderer and extent:
            if ";" in extent:
                extent = extent.split(";")[1]
            geom = QgsGeometry.fromWkt(extent)
            self.extent_renderer.show_feature(geom)

    def leaveEvent(self, event):
        if self.extent_renderer:
            self.extent_renderer.clear_feature()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_layout_state()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_layout_state()
        QTimer.singleShot(0, self._update_layout_state)


class SearchThread(QThread):
    search_started = pyqtSignal()
    search_finished = pyqtSignal()
    data_downloaded = pyqtSignal(object, QByteArray)
    error_occurred = pyqtSignal(object)

    def __init__(
        self,
        search_text: Optional[str],
        mutex: QMutex,
        parent: Optional[QThread] = None,
        geom_filter: Optional[str] = None,
    ) -> None:
        """
        Initialize a thread for performing asynchronous geoservice searches.

        :param search_text: Text string used to search for geoservices.
        :param mutex: QMutex object to synchronize access to shared resources.
        :param parent: Optional parent QThread object.
        :param geom_filter: Optional WKT polygon string to filter search by map extent.
        :return: None
        """
        super().__init__(parent)
        self.search_text = search_text
        self.geom_filter = geom_filter

        self.searcher = Client()
        self.mutex = mutex

        self.img_cach = {}

        self.need_stop = False

    def run(self):
        self.search_started.emit()

        results = []

        # search
        try:
            self.mutex.lock()
            results = self.searcher.get_geoservices(
                search_str=self.search_text,
                intersects_boundary=self.geom_filter,
            )

            ext_results = []
            for result in results:
                if self.need_stop:
                    break
                # get icon
                ba = QByteArray()
                icon_id = result.get("icon")
                if self.img_cach.get(icon_id) is None:
                    if icon_id:
                        ba = QByteArray(
                            self.searcher.get_icon_content(icon_id, 24, 24)
                        )
                    else:
                        ba = QByteArray(self.searcher.get_default_icon(24, 24))
                    self.img_cach[icon_id] = ba
                else:
                    ba = self.img_cach[icon_id]
                # get extent
                extent = result["extent"]
                # area = None
                area = 0.0
                if extent:
                    if extent.startswith("SRID"):
                        extent = extent.split(";")[1]
                    area = QgsGeometry.fromWkt(extent).area()

                ext_results.append([area, result, ba])

            ext_results.sort(key=lambda x: x[0])
            for result in ext_results:
                self.data_downloaded.emit(result[1], result[2])
            self.search_finished.emit()
        except URLError:
            error_text = (self.tr("Network error!\n{0}")).format(
                str(sys.exc_info()[1])
            )
            # error_text = 'net'
            self.error_occurred.emit(error_text)
        except ConnectionError:
            error_text = (self.tr("Network error: {0}")).format(
                str(sys.exc_info()[1])
            )
            self.error_occurred.emit(error_text)
        except Exception:
            error_text = (self.tr("Error of processing!\n{0}: {1}")).format(
                str(sys.exc_info()[0].__name__), str(sys.exc_info()[1])
            )
            # error_text = 'common'
            self.error_occurred.emit(error_text)

        self.mutex.unlock()

    def stop(self):
        self.need_stop = True
