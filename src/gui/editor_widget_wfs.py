import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QMessageBox

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_wfs.ui'))


class EditorWidgetWfs(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetWfs, self).__init__(parent)
        self.setupUi(self)
        self.wfs_validator = LineEditColorValidator(self.txtUrl, 'http[s]?://.+', error_tooltip='http{s}://any_text')
        # self.txtUrl.textChanged.connect(self.set_layers_names)

    def feel_form(self, ds_info):
        self.ds_info = ds_info
        self.txtUrl.setText(ds_info.wfs_url)
        self.txtParams.setText(ds_info.wfs_params)
        self.txtLayers.setText(",".join(ds_info.wfs_layers))
        self.chkTurnOver.setChecked(ds_info.wfs_turn_over if ds_info.wfs_turn_over else False)

    def feel_ds_info(self, ds_info):
        ds_info.wfs_url = self.txtUrl.text()
        ds_info.wfs_params = self.txtParams.text()
        ds_info.wfs_layers = self.txtLayers.text().split()
        ds_info.wfs_turn_over = self.chkTurnOver.isChecked()

    def validate(self, ds_info):
        if not ds_info.wfs_url:
            QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter WFS url'))
            return False

        if not self.wfs_validator.is_valid():
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct value for WMS url'))
                return False

        return True
