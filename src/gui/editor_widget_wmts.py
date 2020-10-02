import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QMessageBox

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_wmts.ui'))


class EditorWidgetWmts(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetWmts, self).__init__(parent)
        self.setupUi(self)
        self.wmts_validator = LineEditColorValidator(self.txtUrl, 'http[s]?://.+', error_tooltip='http{s}://any_text')


    def feel_form(self, ds_info):
        self.ds_info = ds_info
        self.txtUrl.setText(ds_info.wmts_url)
        self.txtParams.setText(ds_info.wmts_params)
        self.txtLayer.setText(ds_info.wmts_layer)

    def feel_ds_info(self, ds_info):
        ds_info.wmts_url = self.txtUrl.text()
        ds_info.wmts_params = self.txtParams.text()
        ds_info.wmts_layer = self.txtLayer.text()

    def validate(self, ds_info):
        if not ds_info.wmts_url:
            QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter WMTS url'))
            return False

        if not self.wmts_validator.is_valid():
            QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct value for WMTS url'))
            return False

        return True