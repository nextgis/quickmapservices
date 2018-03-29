from __future__ import absolute_import
import os
import shutil

from qgis.PyQt import uic
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from os import path

from . import extra_sources
from .data_source_info import DataSourceInfo
from .data_source_serializer import DataSourceSerializer
from .data_sources_list import DataSourcesList
from .group_info import GroupInfo
from .groups_list import GroupsList
from .supported_drivers import KNOWN_DRIVERS
from .gui.editor_widget_gdal import EditorWidgetGdal
from .gui.editor_widget_tms import EditorWidgetTms
from .gui.editor_widget_wms import EditorWidgetWms
from .gui.editor_widget_wfs import EditorWidgetWfs
from .gui.editor_widget_geojson import EditorWidgetGeoJson
from .gui.line_edit_color_validator import LineEditColorValidator
from .plugin_settings import PluginSettings
from .compat2qgis import getOpenFileName

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ds_edit_dialog.ui'))


def is_same(file1, file2):
    return os.path.normcase(os.path.normpath(file1)) == \
                os.path.normcase(os.path.normpath(file2))


class DsEditDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(DsEditDialog, self).__init__(parent)
        self.setupUi(self)

        self.DRV_WIDGETS = {
            KNOWN_DRIVERS.GDAL: EditorWidgetGdal(),
            KNOWN_DRIVERS.TMS: EditorWidgetTms(),
            KNOWN_DRIVERS.WMS: EditorWidgetWms(),
            KNOWN_DRIVERS.WFS: EditorWidgetWfs(),
            KNOWN_DRIVERS.GEOJSON: EditorWidgetGeoJson(),
        }

        # init icon selector
        # self.txtIcon.set_dialog_ext(self.tr('Icons (*.ico *.jpg *.jpeg *.png *.svg);;All files (*.*)'))
        # self.txtIcon.set_dialog_title(self.tr('Select icon for data source'))
        self.iconChooseButton.clicked.connect(self.choose_icon)

        # init combos
        self.init_groups_cmb()
        self.init_types_cmb()
        self.change_spec_tab()

        # validators
        self.id_validator = LineEditColorValidator(self.txtId, '^[A-Za-z0-9_]+$', error_tooltip=self.tr('Any text'))
        self.alias_validator = LineEditColorValidator(self.txtAlias, '^[A-Za-z0-9_ ]+$', error_tooltip=self.tr('Any text'))

        # events
        self.cmbType.currentIndexChanged.connect(self.change_spec_tab)

        # vars
        self.ds_info = None
        self.init_with_existing = False
        self._editor_tab = None

        self.set_icon(
            os.path.join(
                os.path.dirname(__file__),
                'icons',
                'mapservices.png'
            )
        )

    def init_groups_cmb(self):
        ds_groups = GroupsList()
        for ds_group in ds_groups.groups.values():
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

    def fill_ds_info(self, ds_info):
        self.ds_info = ds_info
        self.init_with_existing = False
        # feel fields
        self.feel_common_fields()
        self.feel_specific_fields()

    def choose_icon(self):
        icon_path = getOpenFileName(
            self,
            self.tr('Select icon for data source'),
            PluginSettings.get_default_user_icon_path(),
            self.tr('Icons (*.ico *.jpg *.jpeg *.png *.svg);;All files (*.*)')
        )
        if icon_path != "":
            PluginSettings.set_default_user_icon_path(icon_path)
            self.set_icon(icon_path)

    def set_icon(self, icon_path):
        self.__ds_icon = icon_path
        self.iconPreview.setPixmap(
            QPixmap(self.__ds_icon)
        )

    def feel_common_fields(self):
        self.txtId.setText(self.ds_info.id)
        self.txtAlias.setText(self.ds_info.alias)
        # self.txtIcon.set_path(self.ds_info.icon_path)
        self.set_icon(self.ds_info.icon_path)

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
        for spec_widget in self.DRV_WIDGETS.values():
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

        # replace icon if need
        if not is_same(ds_info.icon_path, self.ds_info.icon_path):
            os.remove(self.ds_info.icon_path)

            dir_path = os.path.dirname(self.ds_info.file_path)

            ico_file_name = path.basename(ds_info.icon_path)
            ico_path = path.join(dir_path, ico_file_name)
            shutil.copy(ds_info.icon_path, ico_path)

        # replace gdal_conf if need
        if ds_info.type == KNOWN_DRIVERS.GDAL:

            def copy_new_gdal_file():
                dir_path = os.path.dirname(self.ds_info.file_path)
                gdal_file_name = path.basename(ds_info.gdal_source_file)
                gdal_file_path = path.join(dir_path, gdal_file_name)
                shutil.copy(ds_info.gdal_source_file, gdal_file_path)

            # old ds = gdal
            if self.ds_info.type == KNOWN_DRIVERS.GDAL:
                if ds_info.gdal_source_file != self.ds_info.gdal_source_file:
                    os.remove(self.ds_info.icon_path)
                    copy_new_gdal_file()
            else:
                copy_new_gdal_file()

        # write config
        DataSourceSerializer.write_to_ini(ds_info, self.ds_info.file_path)

        return True


    def create_new(self, ds_info):
        if not self.check_existing_id(ds_info.id):
            return False

        # set paths
        dir_path = path.join(extra_sources.USER_DIR_PATH, extra_sources.DATA_SOURCES_DIR_NAME, ds_info.id)

        if path.exists(dir_path):
            salt = 0
            while path.exists(dir_path + str(salt)):
                salt += 1
            dir_path += str(salt)

        ini_path = path.join(dir_path, 'metadata.ini')
        ico_path = path.join(dir_path, ds_info.icon)

        # create dir
        os.mkdir(dir_path)

        # copy icon
        shutil.copy(ds_info.icon_path, ico_path)

        if ds_info.type == KNOWN_DRIVERS.GDAL:
            # copy gdal file
            gdal_file_name = path.basename(ds_info.gdal_source_file)
            gdal_file_path = path.join(dir_path, gdal_file_name)
            shutil.copy(ds_info.gdal_source_file, gdal_file_path)

        # write config
        DataSourceSerializer.write_to_ini(ds_info, ini_path)

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
        # ds_info.icon = os.path.basename(self.txtIcon.get_path())
        ds_info.icon = os.path.basename(self.__ds_icon)

        ds_info.lic_name = self.txtLicense.text()
        ds_info.lic_link = self.txtLicenseLink.text()
        ds_info.copyright_text = self.txtCopyrightText.text()
        ds_info.copyright_link = self.txtCopyrightLink.text()
        ds_info.terms_of_use = self.txtTermsOfUse.text()

        ds_info.group = self.cmbGroup.itemData(self.cmbGroup.currentIndex()).id
        ds_info.type = self.cmbType.itemData(self.cmbType.currentIndex())

        self.DRV_WIDGETS[ds_info.type].feel_ds_info(ds_info)

        ds_info.icon_path = self.__ds_icon
        # ds_info.icon_path = self.txtIcon.get_path()

    def validate(self, ds_info):
        # validate common fields
        checks = [
            (ds_info.id, self.tr('Please, enter data source id')),
            (ds_info.alias, self.tr('Please, enter data source alias')),
            (ds_info.icon, self.tr('Please, select icon for data source')),
            (ds_info.group, self.tr('Please, select group for data source')),
            (ds_info.type, self.tr('Please, select type for data source')),
        ]

        for val, comment in checks:
            if not val:
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr(comment))
                return False

        checks_correct = [
            (self.id_validator, self.tr('Please, enter correct value for data source id')),
            (self.alias_validator, self.tr('Please, enter correct value for data source alias')),
        ]

        for val, comment in checks_correct:
            if not val.is_valid():
                QMessageBox.critical(self, self.tr('Error on save data source'), self.tr(comment))
                return False

        # validate special fields
        if not self.DRV_WIDGETS[ds_info.type].validate(ds_info):
            return False

        return True
