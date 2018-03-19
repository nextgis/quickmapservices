import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QMessageBox

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_gdal.ui'))


class EditorWidgetGdal(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetGdal, self).__init__(parent)
        self.setupUi(self)
        # init icon selector
        self.txtGdalFile.set_dialog_ext(self.tr('GDAL Data Source (*.xml);;All files (*.*)'))
        self.txtGdalFile.set_dialog_title(self.tr('Select gdal data source file'))


    def feel_form(self, ds_info):
        self.ds_info = ds_info
        self.txtGdalFile.set_path(self.ds_info.gdal_source_file)


    def feel_ds_info(self, ds_info):
        ds_info.gdal_source_file = self.txtGdalFile.get_path()


    def validate(self, ds_info):
        if not ds_info:
            QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, select GDAL file path'))
            return False

        return True