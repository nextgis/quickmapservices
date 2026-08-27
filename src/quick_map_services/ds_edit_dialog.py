# NextGIS QuickMapServices
# Copyright (C) 2026  NextGIS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

import os
import shutil
from os import path
from typing import Optional

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from quick_map_services.core.settings import QmsSettings
from quick_map_services.data_source_info import DataSourceInfo
from quick_map_services.data_source_serializer import DataSourceSerializer
from quick_map_services.data_sources_list import DataSourcesList
from quick_map_services.group_info import GroupInfo
from quick_map_services.groups_list import GroupsList
from quick_map_services.gui.editor_widget_gdal import EditorWidgetGdal
from quick_map_services.gui.editor_widget_geojson import EditorWidgetGeoJson
from quick_map_services.gui.editor_widget_mvt import EditorWidgetMvt
from quick_map_services.gui.editor_widget_tms import EditorWidgetTms
from quick_map_services.gui.editor_widget_wfs import EditorWidgetWfs
from quick_map_services.gui.editor_widget_wms import EditorWidgetWms
from quick_map_services.gui.line_edit_color_validator import (
    LineEditColorValidator,
)
from quick_map_services.paths_constants import (
    DATA_SOURCES_DIR_NAME,
    USER_DIR_PATH,
)
from quick_map_services.supported_drivers import KNOWN_DRIVERS

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "ds_edit_dialog.ui")
)


def is_same(file1, file2):
    return os.path.normcase(os.path.normpath(file1)) == os.path.normcase(
        os.path.normpath(file2)
    )


class DsEditDialog(QDialog, FORM_CLASS):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Constructor."""
        super(DsEditDialog, self).__init__(parent)
        self.setupUi(self)

        self.DRV_WIDGETS = {
            KNOWN_DRIVERS.GDAL: EditorWidgetGdal(),
            KNOWN_DRIVERS.TMS: EditorWidgetTms(),
            KNOWN_DRIVERS.MVT: EditorWidgetMvt(),
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
        self.id_validator = LineEditColorValidator(
            self.txtId, "^[A-Za-z0-9_]+$", error_tooltip=self.tr("Any text")
        )
        # events
        self.cmbType.currentIndexChanged.connect(self.change_spec_tab)

        # vars
        self.ds_info = None
        self.init_with_existing = False
        self._editor_tab = None

        self.set_icon(
            os.path.join(os.path.dirname(__file__), "icons", "mapservices.png")
        )

    def init_groups_cmb(self):
        ds_groups = GroupsList()
        for ds_group in ds_groups.groups.values():
            self.cmbGroup.addItem(
                QIcon(ds_group.icon), self.tr(ds_group.alias), ds_group
            )

    def init_types_cmb(self):
        for drv in KNOWN_DRIVERS.ALL_DRIVERS:
            self.cmbType.addItem(drv, drv)

    def change_spec_tab(self, index=0):
        # remove old widget
        self.tabWidget.removeTab(2)  # bad!

        drv = self.cmbType.itemData(self.cmbType.currentIndex())
        self.tabWidget.addTab(self.DRV_WIDGETS[drv], drv)

    def set_ds_info(self, data_source: DataSourceInfo) -> None:
        """Populate the dialog to edit an existing data source.

        :param data_source: Existing data source to edit.
        """
        self.ds_info = data_source
        self.init_with_existing = True
        self.fill_common_fields()
        self.fill_specific_fields()

    def set_ds_info_for_copy(self, data_source: DataSourceInfo) -> None:
        """Populate the dialog to create a copy of a data source.

        :param data_source: Data source used as the copy template.
        """
        self.ds_info = data_source
        self.init_with_existing = False
        self.fill_common_fields()
        self.fill_specific_fields()

    @pyqtSlot()
    def choose_icon(self) -> None:
        """
        Open a file dialog to select a custom icon for the data source.

        :return: None
        :rtype: None
        """
        settings = QmsSettings()

        icon_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select icon for data source"),
            settings.default_user_icon_path,
            self.tr("Icons (*.ico *.jpg *.jpeg *.png *.svg);;All files (*.*)"),
        )
        if icon_path:
            settings.default_user_icon_path = icon_path
            self.set_icon(icon_path)

    def set_icon(self, icon_path):
        self.__ds_icon = icon_path
        self.iconPreview.setPixmap(QPixmap(self.__ds_icon))

    def fill_common_fields(self) -> None:
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
            self.cmbGroup.setCurrentIndex(self.cmbGroup.count() - 1)

    def fill_specific_fields(self) -> None:
        data_source_type = self.ds_info.type
        self.cmbType.setCurrentIndex(self.cmbType.findData(data_source_type))
        self.DRV_WIDGETS[data_source_type].fill_form(self.ds_info)

    def accept(self) -> None:
        data_source = DataSourceInfo()
        self._fill_data_source_from_form(data_source)
        if not self.validate(data_source):
            return

        if self.init_with_existing:
            res = self.save_existing(data_source)
        else:
            res = self.create_new(data_source)
        if res:
            super(DsEditDialog, self).accept()

    def save_existing(self, data_source: DataSourceInfo) -> bool:
        if data_source.id != self.ds_info.id and not self.check_existing_id(
            data_source.id
        ):
            return False

        if data_source == self.ds_info:
            return True

        # replace icon if need
        if not is_same(data_source.icon_path, self.ds_info.icon_path):
            os.remove(self.ds_info.icon_path)

            dir_path = os.path.dirname(self.ds_info.file_path)

            icon_file_name = path.basename(data_source.icon_path)
            icon_path = path.join(dir_path, icon_file_name)
            shutil.copy(data_source.icon_path, icon_path)

        # replace gdal_conf if need
        if data_source.type == KNOWN_DRIVERS.GDAL:

            def copy_new_gdal_file() -> None:
                dir_path = os.path.dirname(self.ds_info.file_path)
                gdal_file_name = path.basename(data_source.gdal_source_file)
                gdal_file_path = path.join(dir_path, gdal_file_name)
                shutil.copy(data_source.gdal_source_file, gdal_file_path)

            # old ds = gdal
            if self.ds_info.type == KNOWN_DRIVERS.GDAL:
                if (
                    data_source.gdal_source_file
                    != self.ds_info.gdal_source_file
                ):
                    os.remove(self.ds_info.icon_path)
                    copy_new_gdal_file()
            else:
                copy_new_gdal_file()

        # write config
        DataSourceSerializer.write_to_ini(data_source, self.ds_info.file_path)

        return True

    def create_new(self, data_source: DataSourceInfo) -> bool:
        if not self.check_existing_id(data_source.id):
            return False

        # set paths
        dir_path = path.join(
            USER_DIR_PATH,
            DATA_SOURCES_DIR_NAME,
            data_source.id,
        )

        if path.exists(dir_path):
            salt = 0
            while path.exists(dir_path + str(salt)):
                salt += 1
            dir_path += str(salt)

        ini_path = path.join(dir_path, "metadata.ini")
        ico_path = path.join(dir_path, data_source.icon)

        # create dir
        os.mkdir(dir_path)

        # copy icon
        shutil.copy(data_source.icon_path, ico_path)

        if data_source.type == KNOWN_DRIVERS.GDAL:
            # copy gdal file
            gdal_file_name = path.basename(data_source.gdal_source_file)
            gdal_file_path = path.join(dir_path, gdal_file_name)
            shutil.copy(data_source.gdal_source_file, gdal_file_path)

        # write config
        DataSourceSerializer.write_to_ini(data_source, ini_path)

        return True

    def check_existing_id(self, data_source_id: str) -> bool:
        gl = DataSourcesList()
        if data_source_id in gl.data_sources:
            QMessageBox.critical(
                self,
                self.tr("Error on save group"),
                self.tr(
                    "Data source with such id already exists! Select new id for data source!"
                ),
            )
            return False
        return True

    def _fill_data_source_from_form(
        self,
        data_source: DataSourceInfo,
    ) -> None:
        """Read dialog fields into a data source.

        :param data_source: Data source receiving form values.
        """
        data_source.id = self.txtId.text()
        data_source.alias = self.txtAlias.text()
        # ds_info.icon = os.path.basename(self.txtIcon.get_path())
        data_source.icon = os.path.basename(self.__ds_icon)

        data_source.lic_name = self.txtLicense.text()
        data_source.lic_link = self.txtLicenseLink.text()
        data_source.copyright_text = self.txtCopyrightText.text()
        data_source.copyright_link = self.txtCopyrightLink.text()
        data_source.terms_of_use = self.txtTermsOfUse.text()

        data_source.group = self.cmbGroup.itemData(
            self.cmbGroup.currentIndex()
        ).id
        data_source.type = self.cmbType.itemData(self.cmbType.currentIndex())

        self.DRV_WIDGETS[data_source.type].fill_ds_info(data_source)

        data_source.icon_path = self.__ds_icon
        # ds_info.icon_path = self.txtIcon.get_path()

    def validate(self, data_source: DataSourceInfo) -> bool:
        # validate common fields
        checks = [
            (data_source.id, self.tr("Please, enter data source id")),
            (data_source.alias, self.tr("Please, enter data source alias")),
            (data_source.icon, self.tr("Please, select icon for data source")),
            (
                data_source.group,
                self.tr("Please, select group for data source"),
            ),
            (data_source.type, self.tr("Please, select type for data source")),
        ]

        for val, comment in checks:
            if not val:
                QMessageBox.critical(
                    self,
                    self.tr("Error on save data source"),
                    self.tr(comment),
                )
                return False

        checks_correct = [
            (
                self.id_validator,
                self.tr("Please, enter correct value for data source id"),
            ),
        ]

        for val, comment in checks_correct:
            if not val.is_valid():
                QMessageBox.critical(
                    self,
                    self.tr("Error on save data source"),
                    self.tr(comment),
                )
                return False

        # validate special fields
        if not self.DRV_WIDGETS[data_source.type].validate(data_source):
            return False

        return True
