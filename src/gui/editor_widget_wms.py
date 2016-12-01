import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QMessageBox

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_wms.ui'))


class EditorWidgetWms(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetWms, self).__init__(parent)
        self.setupUi(self)
        self.wms_validator = LineEditColorValidator(self.txtUrl, 'http[s]?://.+', error_tooltip='http{s}://any_text')


    def feel_form(self, ds_info):
        self.ds_info = ds_info
        self.txtUrl.setText(ds_info.wms_url)
        self.txtParams.setText(ds_info.wms_params + "&" + ds_info.wms_url_params)
        self.txtLayers.setText(ds_info.wms_layers)
        self.chkTurnOver.setChecked(ds_info.wms_turn_over if ds_info.wms_turn_over else False)

    def feel_ds_info(self, ds_info):
        ds_info.wms_url = self.txtUrl.text()
        ds_info.wms_params = self.txtParams.text()
        ds_info.wms_layers = self.txtLayers.text()
        ds_info.wms_turn_over = self.chkTurnOver.isChecked()

    def validate(self, ds_info):
        if not ds_info.wms_url:
            QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter WMS url'))
            return False

        if not self.wms_validator.is_valid():
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct value for WMS url'))
                return False

        return True