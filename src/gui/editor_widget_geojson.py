import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QMessageBox

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_geojson.ui'))


class EditorWidgetGeoJson(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetGeoJson, self).__init__(parent)
        self.setupUi(self)
        self.geojson_validator = LineEditColorValidator(self.txtUrl, 'http[s]?://.+', error_tooltip='http{s}://any_text')

    def feel_form(self, ds_info):
        self.ds_info = ds_info
        self.txtUrl.setText(ds_info.geojson_url)

    def feel_ds_info(self, ds_info):
        ds_info.geojson_url = self.txtUrl.text()

    def validate(self, ds_info):
        if not ds_info.geojson_url:
            QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter GeoJSON url'))
            return False

        if not self.geojson_validator.is_valid():
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct value for GeoJSON url'))
                return False

        return True
