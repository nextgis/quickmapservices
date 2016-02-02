import ConfigParser
import codecs
import os
import shutil

from PyQt4 import uic
from PyQt4.QtGui import QDialog, QIcon, QMessageBox
from os import path

from data_source_info import DataSourceInfo
from data_sources_list import DataSourcesList
from group_info import GroupInfo
from groups_list import GroupsList
from supported_drivers import KNOWN_DRIVERS
from .gui.editor_widget_gdal import EditorWidgetGdal
from .gui.editor_widget_tms import EditorWidgetTms
from .gui.editor_widget_wms import EditorWidgetWms
from .gui.line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ds_edit_dialog.ui'))


class DsEditDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(DsEditDialog, self).__init__(parent)
        self.setupUi(self)

        self.DRV_WIDGETS = {
            KNOWN_DRIVERS.GDAL: EditorWidgetGdal(),
            KNOWN_DRIVERS.TMS: EditorWidgetTms(),
            KNOWN_DRIVERS.WMS: EditorWidgetWms()
        }

        # init icon selector
        self.txtIcon.set_dialog_ext(self.tr('Icons (*.ico);;Jpeg (*.jpg);;Png (*.png);;All files (*.*)'))
        self.txtIcon.set_dialog_title(self.tr('Select icon for data source'))

        # init combos
        self.init_groups_cmb()
        self.init_types_cmb()
        self.change_spec_tab()

        # validators
        self.id_validator = LineEditColorValidator(self.txtId, '^[A-Za-z0-9_]+$', error_tooltip=self.tr('Any text'))
        self.alias_validator = LineEditColorValidator(self.txtAlias, '^.+$', error_tooltip=self.tr('Any text'))

        # events
        self.cmbType.currentIndexChanged.connect(self.change_spec_tab)

        # vars
        self.ds_info = None
        self.init_with_existing = False
        self._editor_tab = None


    def init_groups_cmb(self):
        ds_groups = GroupsList()
        for ds_group in ds_groups.groups.itervalues():
            self.cmbGroup.addItem(QIcon(ds_group.icon), self.tr(ds_group.alias), ds_group)

    def init_types_cmb(self):
        for drv in KNOWN_DRIVERS.ALL_DRIVERS:
            self.cmbType.addItem(drv, drv)

    def change_spec_tab(self, index=0):
        # remove old widget
        self.tabWidget.removeTab(2)  # bad!

        drv = self.cmbType.itemData(self.cmbType.currentIndex())
        self.tabWidget.addTab(self.DRV_WIDGETS[drv], drv)


    def set_ds_info(self, ds_info):
        self.ds_info = ds_info
        self.init_with_existing = True
        # feel fields
        self.feel_common_fields()
        self.feel_specific_fields()

    def feel_common_fields(self):
        self.txtId.setText(self.ds_info.id)
        self.txtAlias.setText(self.ds_info.alias)
        self.txtIcon.set_path(self.ds_info.icon)

        # license
        self.txtLicense.setText(self.ds_info.lic_name)
        self.txtLicenseLink.setText(self.ds_info.lic_link)
        self.txtCopyrightText.setText(self.ds_info.copyright_text)
        self.txtCopyrightLink.setText(self.ds_info.copyright_link)
        self.txtTermsOfUse.setText(self.ds_info.terms_of_use)

        # set group
        group_index = None
        for i in range(self.cmbGroup.count()):
            if self.cmbGroup.itemData(i).id == self.ds_info.group:
                group_index = i
                break
        if group_index is not None:
            self.cmbGroup.setCurrentIndex(i)
        else:
            non_ex_group = GroupInfo(group_id=self.ds_info.group)
            self.cmbGroup.addItem(self.ds_info.group, non_ex_group)
            self.cmbGroup.setCurrentIndex(self.cmbGroup.count()-1)

    def feel_specific_fields(self):
        # set type
        self.cmbType.setCurrentIndex(self.cmbType.findData(self.ds_info.type))
        # feel widgets
        for spec_widget in self.DRV_WIDGETS.itervalues():
            spec_widget.feel_form(self.ds_info)


    def accept(self):
        new_ds_info = DataSourceInfo()
        self.feel_ds_info(new_ds_info)
        if not self.validate(new_ds_info):
            return

        if self.init_with_existing:
            res = self.save_existing(new_ds_info)
        else:
            res = self.create_new(new_ds_info)
        if res:
            super(DsEditDialog, self).accept()


    def save_existing(self, ds_info):
        if ds_info.id != self.ds_info.id and not self.check_existing_id(ds_info.id):
            return False

        if ds_info == self.ds_info:
            return True

        # # replace icon if need
        # if ds_info.icon_path != self.ds_info.icon_path:
        #     os.remove(self.ds_info.icon_path)
        #
        #     dir_path = os.path.abspath(os.path.join(self.ds_info.file_path, os.path.pardir))
        #
        #     ico_file_name = path.basename(ds_info.icon_path)
        #     ico_path = path.join(dir_path, ico_file_name)
        #
        #     shutil.copy(ds_info.icon_path, ico_path)
        #
        # self.write_config_file(ds_info, self.ds_info.file_path)

        return True

    def create_new(self):
        return True

    def check_existing_id(self, ds_id):
        gl = DataSourcesList()
        if ds_id in gl.data_sources.keys():
            QMessageBox.critical(self, self.tr('Error on save group'),
                                 self.tr('Data source with such id already exists! Select new id for data source!'))
            return False
        return True

    def feel_ds_info(self, ds_info):
        ds_info.id = self.txtId.text()
        ds_info.alias = self.txtAlias.text()
        ds_info.icon = self.txtIcon.get_path()

        ds_info.lic_name = self.txtLicense.text()
        ds_info.lic_link = self.txtLicenseLink.text()
        ds_info.copyright_text = self.txtCopyrightText.text()
        ds_info.copyright_link = self.txtCopyrightLink.text()
        ds_info.terms_of_use = self.txtTermsOfUse.text()

        ds_info.group = self.cmbGroup.itemData(self.cmbGroup.currentIndex()).id
        ds_info.type = self.cmbType.itemData(self.cmbType.currentIndex())

        self.DRV_WIDGETS[ds_info.type].feel_ds_info(ds_info)


    def validate(self, ds_info):
        # validate common fields
        checks = [
            (ds_info.id, 'Please, enter data source id'),
            (ds_info.alias, 'Please, enter data source alias'),
            (ds_info.icon, 'Please, select icon for data source'),
            (ds_info.group, 'Please, select group for data source'),
            (ds_info.type, 'Please, select type for data source'),
        ]

        for val, comment in checks:
            if not val:
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr(comment))
                return False

        if not self.DRV_WIDGETS[ds_info.type].validate(ds_info):
            return False

        return True


