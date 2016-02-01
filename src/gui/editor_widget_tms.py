import os

from PyQt4 import uic
from PyQt4.QtGui import QWidget, QIntValidator, QMessageBox

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_tms.ui'))


class EditorWidgetTms(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetTms, self).__init__(parent)
        self.setupUi(self)
        self.wms_validator = LineEditColorValidator(self.txtUrl, 'http[s]?://.+', error_tooltip='http{s}://any_text/{z}/{x}/{y}/')
        self.txtCrsId.setValidator(QIntValidator())
        self.txtPostgisCrsId.setValidator(QIntValidator())
        #self.txtCrsId.clicked.connect(lambda: self.rbnCrsId.setChecked(True))
        #self.txtPostgisCrsId.clicked.connect(lambda: self.rbPostgisCrsId.setChecked(True))
        #self.spnCustomProj.clicked.connect(lambda: self.rbCustomProj.setChecked(True))

    def feel_form(self, ds_info):
        self.ds_info = ds_info

        self.txtUrl.setText(ds_info.tms_url)
        self.spbZMin.setValue(int(ds_info.tms_zmin) if ds_info.tms_zmin else self.spbZMin.value())
        self.spbZMax.setValue(int(ds_info.tms_zmax) if ds_info.tms_zmax else self.spbZMax.value())
        self.chkOriginTop.setChecked(ds_info.tms_y_origin_top if ds_info.tms_y_origin_top else False)

        if self.ds_info.tms_epsg_crs_id:
            self.txtCrsId.setText(str(self.ds_info.tms_epsg_crs_id))
            self.rbCrsId.setChecked(True)
        if self.ds_info.tms_postgis_crs_id:
            self.txtPostgisCrsId.setText(str(self.ds_info.tms_postgis_crs_id))
            self.rbPostgisCrsId.setChecked(True)
        if self.ds_info.tms_custom_proj:
            self.txtCustomProj.setText(self.ds_info.tms_custom_proj)
            self.rbCustomProj.setChecked(True)


    def feel_ds_info(self, ds_info):
        ds_info.tms_url = self.txtUrl.text()
        ds_info.tms_zmin = self.spbZMin.value()
        ds_info.tms_zmax = self.spbZMax.value()
        ds_info.tms_y_origin_top = self.chkOriginTop.isChecked()

        if self.rbCrsId.isChecked():
            try:
                code = int(self.txtCrsId.text())
                ds_info.tms_epsg_crs_id = code
            except:
                pass
            return
        if self.rbPostgisCrsId.isChecked():
            try:
                code = int(self.txtPostgisCrsId.text())
                ds_info.tms_postgis_crs_id = code
            except:
                pass
            return
        if self.txtCustomProj.isChecked():
            ds_info.tms_custom_proj = self.txtCustomProj.text()
            return


    def validate(self, ds_info):
        if not ds_info.tms_url:
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter TMS url'))
                return False

        if self.rbCrsId.isChecked():
            try:
                code = int(self.txtCrsId.text())
            except:
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct CRC ID'))
                return False

        if self.rbPostgisCrsId.isChecked():
            try:
                code = int(self.txtPostgisCrsId.text())
            except:
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct PostGIS CRC ID'))
                return False

        return True