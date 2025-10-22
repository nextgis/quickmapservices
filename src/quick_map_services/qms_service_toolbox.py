import ast
import sys
from datetime import datetime, timezone
from os import path
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import URLError

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsMessageLog,
    QgsSettings,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import (
    QByteArray,
    QLocale,
    QMutex,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from qgis.PyQt.QtGui import (
    QCursor,
    QImage,
    QPixmap,
)
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDockWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from .data_source_serializer import DataSourceSerializer
from .plugin_settings import PluginSettings
from .qgis_map_helpers import add_layer_to_map
from .qgis_settings import QGISSettings
from .qms_external_api_python.api.api_abstract import QmsNews
from .qms_external_api_python.client import Client
from .qms_news import News
from .rb_result_renderer import RubberBandResultRenderer
from .singleton import singleton


def plPrint(msg, level=Qgis.Info):
    QgsMessageLog.logMessage(msg, "QMS", level)


STATUS_FILTER_ALL = "all"
STATUS_FILTER_ONLY_WORKS = "works"


class Geoservice:
    def __init__(self, attributes, image_qByteArray):
        self.attributes = attributes
        self.image_qByteArray = image_qByteArray

    def isValid(self):
        return self.attributes.get("id") is not None

    @property
    def id(self):
        return self.attributes.get("id")

    def saveSelf(self, qSettings):
        qSettings.setValue(f"{self.id}/json", str(self.attributes))
        qSettings.setValue(f"{self.id}/image", self.image_qByteArray)

    def loadSelf(self, id, qSettings):
        service_json = qSettings.value(f"{self.id}/json", None)
        self.attributes = ast.literal_eval(service_json)
        self.image_qByteArray = settings.value(
            f"{self.id}/image", type=QByteArray
        )


@singleton
class CachedServices:
    def __init__(self):
        self.geoservices = []
        self.load_last_used_services()

    def load_last_used_services(self):
        for geoservice, image_ba in PluginSettings.get_last_used_services():
            geoservice = Geoservice(geoservice, image_ba)
            if geoservice.isValid:
                self.geoservices.append(geoservice)

    def add_service(self, geoservice, image_ba):
        new_gs = Geoservice(geoservice, image_ba)
        geoservices4store = [new_gs]

        for gs in self.geoservices:
            if gs.id == new_gs.id:
                continue
            geoservices4store.append(gs)

        self.geoservices = geoservices4store[0:5]
        PluginSettings.set_last_used_services(self.geoservices)

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
        PluginSettings.set_last_used_services(self.geoservices)

    def get_cached_services(self):
        return [
            (geoservice.attributes, geoservice.image_qByteArray)
            for geoservice in self.geoservices
        ]


FORM_CLASS, _ = uic.loadUiType(
    path.join(path.dirname(__file__), "qms_service_toolbox.ui")
)


class QmsServiceToolbox(QDockWidget, FORM_CLASS):
    def __init__(self, iface):
        QDockWidget.__init__(self, iface.mainWindow())
        self.setupUi(self)
        self.newsFrame.setVisible(False)

        self.iface = iface
        self.search_threads = None  # []
        self.extent_renderer = RubberBandResultRenderer()

        self.cmbStatusFilter.addItem(self.tr("All"), STATUS_FILTER_ALL)
        self.cmbStatusFilter.addItem(
            self.tr("Valid"), STATUS_FILTER_ONLY_WORKS
        )
        self.cmbStatusFilter.currentIndexChanged.connect(self.start_search)

        if hasattr(self.txtSearch, "setPlaceholderText"):
            self.txtSearch.setPlaceholderText(self.tr("Search string..."))

        self.delay_timer = QTimer(self)
        self.delay_timer.setSingleShot(True)
        self.delay_timer.setInterval(250)

        self.delay_timer.timeout.connect(self.start_search)
        self.txtSearch.textChanged.connect(self.delay_timer.start)
        self.btnFilterByExtent.toggled.connect(self.toggle_filter_button)
        self.one_process_work = QMutex()

        self.add_last_used_services()

        self.show_news()

    def show_news(self):
        self.newsFrame.setVisible(False)

        override_locale = QgsSettings().value(
            "locale/overrideFlag", defaultValue=False, type=bool
        )
        if not override_locale:
            locale_full_name = QLocale.system().name()
        else:
            locale_full_name = QgsSettings().value("locale/userLocale", "")

        short_locale = locale_full_name[0:2]

        utm_template = "&".join(
            [
                "utm_source=qgis_plugin",
                "utm_medium=banner",
                "utm_campaign={campaign}",
                f"utm_term={Path(__file__).parent.name}",
                f"utm_content={short_locale}",
            ]
        )

        utm = utm_template.format(campaign="constant")
        bf24_utm = utm_template.format(campaign="black-friday24")

        qms_black_friday_news = QmsNews(
            {
                "ru": f'<a href="https://data.nextgis.com/?{bf24_utm}">Свежие геоданные</a> для проекта. <b>Экономия 50%!</b>',
                "en": f'<a href="https://data.nextgis.com/?{bf24_utm}">Fresh geodata</a> for your project <b>(50% off!)</b>',
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
            year=2024, month=11, day=26, hour=21, minute=1, tzinfo=timezone.utc
        )
        black_friday_finish = datetime(
            year=2024, month=12, day=3, hour=5, minute=59, tzinfo=timezone.utc
        )
        black_friday_news = News(
            qms_black_friday_news,
            date_start=black_friday_start,
            date_finish=black_friday_finish,
            icon="fire.png",
        )
        ordinary_news = News(qms_news)

        self.newsFrame.setVisible(False)
        for news in [black_friday_news, ordinary_news]:
            if news.is_time_to_show():
                self.newsLabel.setText(news.html)
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
        self.add_last_used_services()

    def start_search(self):
        search_text = None
        geom_filter = None
        min_search_text_len = 3

        # status filter
        status_filter = None
        sel_value = self.cmbStatusFilter.itemData(
            self.cmbStatusFilter.currentIndex()
        )
        if sel_value != STATUS_FILTER_ALL:
            status_filter = sel_value

        if not self.btnFilterByExtent.isChecked():
            # text search
            search_text = str(self.txtSearch.text())

            if not search_text:
                self.lstSearchResult.clear()
                self.add_last_used_services()
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
                crsDest = QgsCoordinateReferenceSystem.fromEpsgId(
                    4326
                )  # WGS 84
                xform = QgsCoordinateTransform(map_crs, crsDest)
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
            status_filter=status_filter,
        )
        searcher.data_downloaded.connect(self.show_result)
        searcher.error_occurred.connect(self.show_error)
        searcher.search_started.connect(self.search_started_process)
        searcher.search_finished.connect(self.search_finished_progress)
        self.search_threads = searcher
        searcher.start()

    def add_last_used_services(self) -> None:
        """
        Populate the search result list with recently used geoservices.

        :return: None
        :rtype: None
        """
        services = CachedServices().get_cached_services()
        if len(services) == 0:
            return

        self.lstSearchResult.insertItem(0, self.tr("Last used:"))
        # l = QLabel(self.tr("Last used:"))
        # l.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # self.lSearchResult.addWidget(l)

        for attributes, image_qByteArray in services:
            custom_widget = QmsSearchResultItemWidget(
                attributes, image_qByteArray
            )
            custom_widget.service_not_found.connect(
                self._handle_remove_not_found_cached_service
            )
            custom_widget.service_unavailable.connect(
                self._handle_service_unavailable
            )
            new_item = QListWidgetItem(self.lstSearchResult)
            new_item.setSizeHint(custom_widget.sizeHint())
            self.lstSearchResult.addItem(new_item)
            self.lstSearchResult.setItemWidget(new_item, custom_widget)
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
            custom_widget = QmsSearchResultItemWidget(
                geoservice, image_ba, extent_renderer=self.extent_renderer
            )
            custom_widget.service_not_found.connect(
                lambda _: self._handle_service_unavailable(
                    self.tr("The requested service could not be found.")
                )
            )
            custom_widget.service_unavailable.connect(
                self._handle_service_unavailable
            )
            new_item = QListWidgetItem(self.lstSearchResult)
            new_item.setSizeHint(custom_widget.sizeHint())
            self.lstSearchResult.addItem(new_item)
            self.lstSearchResult.setItemWidget(new_item, custom_widget)

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

    @pyqtSlot(int)
    def _handle_remove_not_found_cached_service(self, service_id: int) -> None:
        """
        Handle the event when a cached service is not found.

        :param service_id: The ID of the service that was not found.
        :type service_id: int
        :return: None
        :rtype: None
        """
        QMessageBox.warning(
            self,
            self.tr("Service not found"),
            self.tr(
                "The service no longer exists and has been removed from the recent list."
            ),
        )

        CachedServices().remove_service(service_id)
        self.refresh_last_used_services()

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


class QmsSearchResultItemWidget(QWidget):
    """
    A custom QWidget representing a single search result item
    in the QuickMapServices (QMS) plugin.
    """

    service_not_found = pyqtSignal(int)
    service_unavailable = pyqtSignal(str)

    def __init__(
        self,
        geoservice: Dict[str, Any],
        image_ba: QByteArray,
        parent: Optional[QWidget] = None,
        extent_renderer: Optional["RubberBandResultRenderer"] = None,
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

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 10, 5, 10)
        self.setLayout(self.layout)

        self.service_icon = QLabel(self)
        self.service_icon.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.service_icon.resize(24, 24)

        qimg = QImage.fromData(image_ba)
        pixmap = QPixmap.fromImage(qimg)
        self.service_icon.setPixmap(pixmap)
        self.layout.addWidget(self.service_icon)

        self.service_desc_layout = QGridLayout()
        self.service_desc_layout.setSpacing(0)
        self.layout.addLayout(self.service_desc_layout)

        self.service_name = QLabel(self)
        self.service_name.setTextFormat(Qt.TextFormat.RichText)
        self.service_name.setWordWrap(True)
        self.service_name.setText(
            "   <strong> {} </strong>".format(geoservice.get("name", ""))
        )
        self.service_desc_layout.addWidget(self.service_name, 0, 0, 1, 3)

        self.service_type = QLabel(self)
        self.service_type.setTextFormat(Qt.TextFormat.RichText)
        self.service_type.setWordWrap(True)
        self.service_type.setText(geoservice.get("type", "").upper() + " ")
        self.service_desc_layout.addWidget(self.service_type, 1, 0)

        self.service_deteils = QLabel(self)
        self.service_deteils.setTextFormat(Qt.TextFormat.RichText)
        self.service_deteils.setWordWrap(True)
        self.service_deteils.setOpenExternalLinks(True)
        self.service_deteils.setText(
            '<a href="{0}">{1}</a>, '.format(
                Client().geoservice_info_url(geoservice.get("id", "")),
                self.tr("details"),
            )
        )
        self.service_desc_layout.addWidget(self.service_deteils, 1, 1)

        self.service_report = QLabel(self)
        self.service_report.setTextFormat(Qt.TextFormat.RichText)
        self.service_report.setWordWrap(True)
        self.service_report.setOpenExternalLinks(True)
        self.service_report.setText(
            '<a href="{0}">{1}</a>'.format(
                Client().geoservice_report_url(geoservice.get("id", "")),
                self.tr("report a problem"),
            )
        )
        self.service_desc_layout.addWidget(self.service_report, 1, 2)
        self.service_desc_layout.setColumnStretch(2, 1)

        self.addButton = QToolButton()
        self.addButton.setText(self.tr("Add"))
        self.addButton.clicked.connect(self.addToMap)
        self.layout.addWidget(self.addButton)

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )

        self.geoservice = geoservice
        self.image_ba = image_ba

    @pyqtSlot()
    def addToMap(self) -> None:
        """
        Try to add the selected geoservice to the map.
        """
        try:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            client = Client()
            client.set_proxy(*QGISSettings.get_qgis_proxy())
            try:
                geoservice_info = client.get_geoservice_info(self.geoservice)
            except ConnectionError as error:
                QApplication.restoreOverrideCursor()
                error_code, message = error.args

                if error_code in (
                    QNetworkReply.NetworkError.ContentNotFoundError,
                    QNetworkReply.NetworkError.ContentGoneError,
                ):
                    self.service_not_found.emit(self.geoservice.get("id"))
                    return

                self.service_unavailable.emit(message)
                return

            except ValueError:
                QApplication.restoreOverrideCursor()
                self.service_unavailable.emit(
                    self.tr("Failed to read service data")
                )
                return

            ds = DataSourceSerializer.read_from_json(geoservice_info)
            add_layer_to_map(ds)

            CachedServices().add_service(self.geoservice, self.image_ba)
        except Exception as ex:
            plPrint(str(ex))
            pass
        finally:
            QApplication.restoreOverrideCursor()

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


class SearchThread(QThread):
    search_started = pyqtSignal()
    search_finished = pyqtSignal()
    data_downloaded = pyqtSignal(object, QByteArray)
    error_occurred = pyqtSignal(object)

    def __init__(
        self,
        search_text,
        mutex,
        parent=None,
        geom_filter=None,
        status_filter=None,
    ):
        QThread.__init__(self, parent)
        self.search_text = search_text
        self.geom_filter = geom_filter
        self.status_filter = status_filter

        self.searcher = Client()
        self.searcher.set_proxy(*QGISSettings.get_qgis_proxy())
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
                cumulative_status=self.status_filter,
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
