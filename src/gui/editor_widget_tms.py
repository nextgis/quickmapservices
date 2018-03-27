import os

from qgis.PyQt import uic
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import QWidget, QMessageBox, QApplication

from .line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'editor_widget_tms.ui'))


class EditorWidgetTms(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(EditorWidgetTms, self).__init__(parent)
        self.setupUi(self)
        self.tms_validator = LineEditColorValidator(self.txtUrl, 'http[s]?://.+', error_tooltip='http{s}://any_text/{z}/{x}/{y}/')
        self.txtCrsId.setValidator(QIntValidator())
        self.txtPostgisCrsId.setValidator(QIntValidator())

        QApplication.instance().focusChanged.connect(self.focus_changed)


    def focus_changed(self, old_w, new_w):
        remap = {
            self.txtCrsId: self.rbCrsId,
            self.txtPostgisCrsId: self.rbPostgisCrsId,
            self.spnCustomProj: self.rbCustomProj
        }

        for cont, rb in remap.items():
            if new_w == cont:
                rb.setChecked(True)


    def feel_form(self, ds_info):
        self.ds_info = ds_info

        self.txtUrl.setText(ds_info.tms_url)
        self.spbZMin.setValue(int(ds_info.tms_zmin) if ds_info.tms_zmin else self.spbZMin.value())
        self.spbZMax.setValue(int(ds_info.tms_zmax) if ds_info.tms_zmax else self.spbZMax.value())
        self.chkOriginTop.setChecked(True if (
            ds_info.tms_y_origin_top is None or
            ds_info.tms_y_origin_top == 1) else False)

        if self.ds_info.tms_epsg_crs_id:
            self.txtCrsId.setText(str(self.ds_info.tms_epsg_crs_id))
            self.rbCrsId.setChecked(True)
            return
        if self.ds_info.tms_postgis_crs_id:
            self.txtPostgisCrsId.setText(str(self.ds_info.tms_postgis_crs_id))
            self.rbPostgisCrsId.setChecked(True)
            return
        if self.ds_info.tms_custom_proj:
            self.txtCustomProj.setText(self.ds_info.tms_custom_proj)
            self.rbCustomProj.setChecked(True)
            return
        # not setted. set default
        self.txtCrsId.setText(str(3857))
        self.rbCrsId.setChecked(True)



    def feel_ds_info(self, ds_info):
        ds_info.tms_url = self.txtUrl.text()
        ds_info.tms_zmin = self.spbZMin.value()
        ds_info.tms_zmax = self.spbZMax.value()
        ds_info.tms_y_origin_top = int(self.chkOriginTop.isChecked())

        if self.rbCrsId.isChecked():
            try:
                code = int(self.txtCrsId.text())
                if code != 3857:
                    ds_info.tms_epsg_crs_id = code
            except:
                pass
            return
        if self.rbPostgisCrsId.isChecked():
            try:
                code = int(self.txtPostgisCrsId.text())
                if code != 3857:
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

        if not self.tms_validator.is_valid():
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr('Please, enter correct value for TMS url'))
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
