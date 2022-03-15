from __future__ import absolute_import

import ast
import sys

from os import path

from qgis.PyQt import uic

from qgis.PyQt.QtGui import (
    QImage,
    QPixmap,
    QCursor,
    QFont,
)

from qgis.PyQt.QtWidgets import (
    QApplication,
    QWidget,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QSizePolicy,
    QListWidgetItem,
    QGridLayout,
)

from qgis.PyQt.QtCore import (
    QThread,
    pyqtSignal,
    Qt,
    QTimer,
    QMutex,
    QByteArray
)

from qgis.core import (
    QgsMessageLog,
    QgsGeometry
)

from .rb_result_renderer import RubberBandResultRenderer
from .data_source_serializer import DataSourceSerializer
from .qgis_map_helpers import add_layer_to_map
from .qms_external_api_python.client import Client
from .qms_external_api_python.api.api_abstract import QmsNews
from .qgis_settings import QGISSettings
from .plugin_settings import PluginSettings
from .singleton import singleton
from .compat import URLError
from .compat2qgis import QGisMessageLogLevel, getCanvasDestinationCrs, QgsCoordinateTransform, QgsCoordinateReferenceSystem

from .qms_news import News


def plPrint(msg, level=QGisMessageLogLevel.Info):
    QgsMessageLog.logMessage(
        msg,
        "QMS",
        level
    )

STATUS_FILTER_ALL = 'all'
STATUS_FILTER_ONLY_WORKS = 'works'

class Geoservice(object):
    def __init__(self, attributes, image_qByteArray):
        self.attributes = attributes
        self.image_qByteArray = image_qByteArray

    def isValid(self):
        return self.attributes.get("id") is not None

    @property
    def id(self):
        return self.attributes.get("id")

    def saveSelf(self, qSettings):
        qSettings.setValue(
            "{}/json".format(self.id),
            unicode(self.attributes)
        )
        qSettings.setValue(
            "{}/image".format(self.id),
            self.image_qByteArray
        )

    def loadSelf(self, id, qSettings):
        service_json = qSettings.value("{}/json".format(self.id), None)
        self.attributes = ast.literal_eval(service_json)
        self.image_qByteArray = settings.value("{}/image".format(self.id), type=QByteArray)


@singleton
class CachedServices(object):
    def __init__(self):
        self.geoservices = []
        self.load_last_used_services()
    
    def load_last_used_services(self):
        for geoservice, image_ba in PluginSettings.get_last_used_services():
            geoservice = Geoservice( geoservice, image_ba)
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

    def get_cached_services(self):
        return [(geoservice.attributes, geoservice.image_qByteArray) for geoservice in self.geoservices]


FORM_CLASS, _ = uic.loadUiType(path.join(
    path.dirname(__file__), 'qms_service_toolbox.ui'))


class QmsServiceToolbox(QDockWidget, FORM_CLASS):
    def __init__(self, iface):
        QDockWidget.__init__(self, iface.mainWindow())
        self.setupUi(self)
        self.newsFrame.setVisible(False)

        self.iface = iface
        self.search_threads = None  # []
        self.extent_renderer = RubberBandResultRenderer()

        self.cmbStatusFilter.addItem(self.tr('All'), STATUS_FILTER_ALL)
        self.cmbStatusFilter.addItem(self.tr('Valid'), STATUS_FILTER_ONLY_WORKS)
        self.cmbStatusFilter.currentIndexChanged.connect(self.start_search)

        if hasattr(self.txtSearch, 'setPlaceholderText'):
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
        client = Client()
        client.set_proxy(*QGISSettings.get_qgis_proxy())
        
        #qms_news = client.get_news()
        qms_news = QmsNews({'ru': u'<a href="https://data.nextgis.com/ru?source=qgis">\u0421\u0432\u0435\u0436\u0438\u0435 \u0433\u0435\u043e\u0434\u0430\u043d\u043d\u044b\u0435 \u0434\u043b\u044f \u043f\u0440\u043e\u0435\u043a\u0442\u0430</a>', 'en': u'<a href="https://data.nextgis.com/en?source=qgis">Fresh geodata</a> for your project'})

        if qms_news is None:
            self.newsFrame.setVisible(False)
            return

        news = News(qms_news)

        if news.is_time_to_show():
            self.newsLabel.setText(news.html)
            self.newsFrame.setVisible(True)
        else:
            self.newsFrame.setVisible(False)

    def toggle_filter_button(self, checked):
        self.txtSearch.setDisabled(checked)
        if checked:
            self.iface.mapCanvas().extentsChanged.connect(self.start_search)
            self.iface.mapCanvas().destinationCrsChanged.connect(self.start_search)
            self.start_search()
        else:
            self.iface.mapCanvas().extentsChanged.disconnect(self.start_search)
            self.iface.mapCanvas().destinationCrsChanged.disconnect(self.start_search)

    def stop_search_thread(self):
        self.search_threads.data_downloaded.disconnect()
        self.search_threads.search_finished.disconnect()
        self.search_threads.stop()
        self.search_threads.wait()
        self.search_threads = None

    def start_search(self):
        search_text = None
        geom_filter = None
        min_search_text_len = 3

        # status filter
        status_filter = None
        sel_value = self.cmbStatusFilter.itemData(self.cmbStatusFilter.currentIndex())
        if sel_value != STATUS_FILTER_ALL:
            status_filter = sel_value

        if not self.btnFilterByExtent.isChecked():
            # text search
            search_text = unicode(self.txtSearch.text())

            if not search_text:
                self.lstSearchResult.clear()
                self.add_last_used_services()
                return

            if len(search_text) < min_search_text_len:
                if self.search_threads:
                    self.stop_search_thread()
                self.lstSearchResult.clear()
                self.lstSearchResult.insertItem(0, self.tr('Need at least 3 symbols to start searching...'))
                return
        else:
            # extent filter
            extent = self.iface.mapCanvas().extent()
            map_crs = getCanvasDestinationCrs(self.iface)
            if map_crs.postgisSrid() != 4326:
                crsDest = QgsCoordinateReferenceSystem.fromEpsgId(4326)    # WGS 84
                xform = QgsCoordinateTransform(map_crs, crsDest)
                extent = xform.transform(extent)
            geom_filter = extent.asWktPolygon()

        if self.search_threads:
            self.stop_search_thread()
            self.lstSearchResult.clear()

        searcher = SearchThread(search_text,
                                self.one_process_work,
                                parent=self.iface.mainWindow(),
                                geom_filter=geom_filter,
                                status_filter=status_filter)
        searcher.data_downloaded.connect(self.show_result)
        searcher.error_occurred.connect(self.show_error)
        searcher.search_started.connect(self.search_started_process)
        searcher.search_finished.connect(self.search_finished_progress)
        self.search_threads = searcher
        searcher.start()

    def add_last_used_services(self):
        services = CachedServices().get_cached_services()
        if len(services) == 0:
            return

        self.lstSearchResult.insertItem(0, self.tr("Last used:"))
        # l = QLabel(self.tr("Last used:"))
        # l.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # self.lSearchResult.addWidget(l)

        for attributes, image_qByteArray in services:
            custom_widget = QmsSearchResultItemWidget(
                attributes,
                image_qByteArray
            )
            new_item = QListWidgetItem(self.lstSearchResult)
            new_item.setSizeHint(custom_widget.sizeHint())
            self.lstSearchResult.addItem(new_item)
            self.lstSearchResult.setItemWidget(
                new_item,
                custom_widget
            )
            # self.lSearchResult.addWidget(custom_widget)

        # w = QWidget()
        # w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.lSearchResult.addWidget(w)

    def search_started_process(self):
        self.lstSearchResult.clear()
        self.lstSearchResult.insertItem(0, self.tr('Searching...'))


    def search_finished_progress(self):
        self.lstSearchResult.takeItem(0)
        if self.lstSearchResult.count() == 0:
            new_widget = QLabel()
            new_widget.setTextFormat(Qt.RichText)
            new_widget.setOpenExternalLinks(True)
            new_widget.setWordWrap(True)
            new_widget.setText(
                u"<div align='center'> <strong>{}</strong> </div><div align='center' style='margin-top: 3px'> {} </div>".format(
                    self.tr(u"No results."),
                    self.tr(u"You can add a service to become searchable. Start <a href='{}'>here</a>.").format(
                        u"https://qms.nextgis.com/create"
                    ),
                )
            )
            new_item = QListWidgetItem(self.lstSearchResult)
            new_item.setSizeHint(new_widget.sizeHint())
            self.lstSearchResult.addItem(new_item)
            self.lstSearchResult.setItemWidget(
                new_item,
                new_widget
            )


    def show_result(self, geoservice, image_ba):
        if geoservice:
            custom_widget = QmsSearchResultItemWidget(geoservice, image_ba, extent_renderer=self.extent_renderer)
            new_item = QListWidgetItem(self.lstSearchResult)
            new_item.setSizeHint(custom_widget.sizeHint())
            self.lstSearchResult.addItem(new_item)
            self.lstSearchResult.setItemWidget(
                new_item,
                custom_widget
            )

        else:
            new_item = QListWidgetItem()
            new_item.setText(self.tr('No results!'))
            new_item.setData(Qt.UserRole, None)
            self.lstSearchResult.addItem(new_item)
        self.lstSearchResult.update()


    def show_error(self, error_text):
        self.lstSearchResult.clear()
        new_widget = QLabel()
        new_widget.setTextFormat(Qt.RichText)
        new_widget.setOpenExternalLinks(True)
        new_widget.setWordWrap(True)
        new_widget.setText(
            u"<div align='center'> <strong>{}</strong> </div><div align='center' style='margin-top: 3px'> {} </div>".format(
                self.tr('Error'),
                error_text
            )
        )
        new_item = QListWidgetItem(self.lstSearchResult)
        new_item.setSizeHint(new_widget.sizeHint())
        self.lstSearchResult.addItem(new_item)
        self.lstSearchResult.setItemWidget(
            new_item,
            new_widget
        )


class QmsSearchResultItemWidget(QWidget):
    def __init__(self, geoservice, image_ba, parent=None, extent_renderer=None):
        QWidget.__init__(self, parent)

        self.extent_renderer = extent_renderer

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 10, 5, 10)
        self.setLayout(self.layout)

        self.service_icon = QLabel(self)
        self.service_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.service_icon.resize(24, 24)

        qimg = QImage.fromData(image_ba)
        pixmap = QPixmap.fromImage(qimg)
        self.service_icon.setPixmap(pixmap)
        self.layout.addWidget(self.service_icon)

        self.service_desc_layout = QGridLayout()
        self.service_desc_layout.setSpacing(0)
        self.layout.addLayout(self.service_desc_layout)

        self.service_name = QLabel(self)
        self.service_name.setTextFormat(Qt.RichText)
        self.service_name.setWordWrap(True)
        self.service_name.setText(u"   <strong> {} </strong>".format(geoservice.get('name', u"")))
        self.service_desc_layout.addWidget(self.service_name, 0, 0, 1, 3)

        self.service_type = QLabel(self)
        self.service_type.setTextFormat(Qt.RichText)
        self.service_type.setWordWrap(True)
        self.service_type.setText(geoservice.get('type', u"").upper() + " ")
        self.service_desc_layout.addWidget(self.service_type, 1, 0)

        self.service_deteils = QLabel(self)
        self.service_deteils.setTextFormat(Qt.RichText)
        self.service_deteils.setWordWrap(True)
        self.service_deteils.setOpenExternalLinks(True)
        self.service_deteils.setText(u"<a href=\"{0}\">{1}</a>, ".format(
            Client().geoservice_info_url(geoservice.get('id', u"")),
            self.tr('details')
        ))
        self.service_desc_layout.addWidget(self.service_deteils, 1, 1)

        self.service_report = QLabel(self)
        self.service_report.setTextFormat(Qt.RichText)
        self.service_report.setWordWrap(True)
        self.service_report.setOpenExternalLinks(True)
        self.service_report.setText(u"<a href=\"{0}\">{1}</a><div/>".format(
            Client().geoservice_report_url(geoservice.get('id', u"")),
            self.tr('report a problem')
        ))
        self.service_desc_layout.addWidget(self.service_report, 1, 2)
        self.service_desc_layout.setColumnStretch(2, 1)


        self.status_label = QLabel(self)
        self.status_label.setTextFormat(Qt.RichText)
        self.status_label.setText(u'\u2022')


        status = geoservice.get('cumulative_status', u'')
        if status == 'works':
            self.status_label.setStyleSheet("color: green; font-size: 30px")
        if status == 'failed':
            self.status_label.setStyleSheet("color: red; font-size: 30px")
        if status == 'problematic':
            self.status_label.setStyleSheet("color: yellow; font-size: 30px")
        self.layout.addWidget(self.status_label)


        self.addButton = QToolButton()
        self.addButton.setText(self.tr("Add"))
        self.addButton.clicked.connect(self.addToMap)
        self.layout.addWidget(self.addButton)
        
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.geoservice = geoservice
        self.image_ba = image_ba

    def addToMap(self):
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            client = Client()
            client.set_proxy(*QGISSettings.get_qgis_proxy())
            geoservice_info = client.get_geoservice_info(self.geoservice)
            ds = DataSourceSerializer.read_from_json(geoservice_info)
            add_layer_to_map(ds)

            CachedServices().add_service(self.geoservice, self.image_ba)
        except Exception as ex:
            plPrint(unicode(ex))
            pass
        finally:
            QApplication.restoreOverrideCursor()

    def mouseDoubleClickEvent(self, event):
        self.addToMap()

    def enterEvent(self, event):
        extent = self.geoservice.get('extent', None)
        if self.extent_renderer and extent:
            if ';' in extent:
                extent = extent.split(';')[1]
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

    def __init__(self, search_text, mutex, parent=None, geom_filter=None, status_filter=None):
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
                cumulative_status=self.status_filter
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
                        ba = QByteArray(self.searcher.get_icon_content(icon_id, 24, 24))
                    else:
                        ba = QByteArray(self.searcher.get_default_icon(24, 24))
                    self.img_cach[icon_id] = ba
                else:
                    ba = self.img_cach[icon_id]
                # get extent
                extent = result['extent']
                # area = None
                area = 0.0
                if extent:
                    if extent.startswith('SRID'):
                        extent = extent.split(';')[1]
                    area = QgsGeometry.fromWkt(extent).area()

                ext_results.append([area, result, ba])

            ext_results.sort(key=lambda x: x[0])
            for result in ext_results:
                self.data_downloaded.emit(result[1], result[2])
            self.search_finished.emit()
        except URLError:
                        error_text = (self.tr("Network error!\n{0}")).format(unicode(sys.exc_info()[1]))
                        # error_text = 'net'
                        self.error_occurred.emit(error_text)
        except Exception:
                        error_text = (self.tr("Error of processing!\n{0}: {1}")).format(unicode(sys.exc_info()[0].__name__), unicode(sys.exc_info()[1]))
                        # error_text = 'common'
                        self.error_occurred.emit(error_text)

        self.mutex.unlock()

    def stop(self):
        self.need_stop = True
