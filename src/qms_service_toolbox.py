from urllib2 import URLError
from os import path

from PyQt4 import uic
from PyQt4.QtGui import QDockWidget, QListWidgetItem, QCursor, QApplication # , QMessageBox
from PyQt4.QtCore import QThread, pyqtSignal, Qt

from data_source_serializer import DataSourceSerializer
from qgis_map_helpers import add_layer_to_map
from .qms_external_api_python.client import Client


FORM_CLASS, _ = uic.loadUiType(path.join(
    path.dirname(__file__), 'qms_service_toolbox.ui'))


class QmsServiceToolbox(QDockWidget, FORM_CLASS):
    def __init__(self, iface):
        QDockWidget.__init__(self, iface.mainWindow())
        self.setupUi(self)
        
        self.iface = iface
        self.search_threads = None  # []

        if hasattr(self.txtSearch, 'setPlaceholderText'):
            self.txtSearch.setPlaceholderText(self.tr("Search string..."))

        self.txtSearch.textChanged.connect(self.start_search)

        self.lstSearchResult.itemDoubleClicked.connect(self.result_selected)


    def start_search(self):
        search_text = unicode(self.txtSearch.text())
        if not search_text:
            self.lstSearchResult.clear()
            return

        if 1 == 1 and self.search_threads:
            print 'Kill ', self.search_threads
            self.search_threads.terminate()
            self.search_threads.wait()
            
        self.show_progress()
        searcher = SearchThread(search_text, self.iface.mainWindow())
        searcher.data_downloaded.connect(self.show_result)
        searcher.error_occurred.connect(self.show_error)
        self.search_threads = searcher
        searcher.start()

    def show_progress(self):
        self.lstSearchResult.clear()
        self.lstSearchResult.addItem(self.tr('Searching...'))
        
    def show_result(self, results):
        self.lstSearchResult.clear()
        if results:
            for geoservice in results:
                new_item = QListWidgetItem()
                new_item.setText(unicode(geoservice['name']) +' [%s]' % geoservice['type'].upper())
                new_item.setData(Qt.UserRole, geoservice)
                #todo: remake with cache icons
                self.lstSearchResult.addItem(new_item)
        else:
            new_item = QListWidgetItem()
            new_item.setText(self.tr('No results!'))
            new_item.setData(Qt.UserRole, None)
            self.lstSearchResult.addItem(new_item)

        self.lstSearchResult.update()
            
    def show_error(self, error_text):
        #print error_text
        self.lstSearchResult.clear()
        self.lstSearchResult.addItem(error_text)

    def result_selected(self, current=None, previous=None):
        if current:
            try:
                QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                geoservice = current.data(Qt.UserRole)
                geoservice_info = Client().get_geoservice_info(geoservice)
                ds = DataSourceSerializer.read_from_json(geoservice_info)
                add_layer_to_map(ds)
            except Exception as ex:
                pass
            finally:
                QApplication.restoreOverrideCursor()






class SearchThread(QThread):

    data_downloaded = pyqtSignal(object)
    error_occurred = pyqtSignal(object)    
    
    def __init__(self, search_text, parent=None):
        QThread.__init__(self, parent)
        self.search_text = search_text
        self.searcher = Client()

    def run(self):
        results = []

        # search
        try:
            results = self.searcher.search_geoservices(self.search_text)
        except URLError:
                        import sys
                        error_text = (self.tr("Network error!\n{0}")).format(unicode(sys.exc_info()[1]))
                        #error_text = 'net'
                        self.error_occurred.emit(error_text)
                        return
        except Exception:
                        import sys
                        error_text = (self.tr("Error of processing!\n{0}: {1}")).format(unicode(sys.exc_info()[0].__name__), unicode(sys.exc_info()[1]))
                        #error_text = 'common'
                        self.error_occurred.emit(error_text)
                        return

        self.data_downloaded.emit(results)
