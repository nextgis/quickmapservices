import shutil
from pathlib import Path
from typing import Optional

from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QGroupBox,
    QHeaderView,
    QListWidgetItem,
    QMessageBox,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from quick_map_services.data_sources_list import USER_DS_PATHS, DataSourcesList
from quick_map_services.data_sources_model import DSManagerModel
from quick_map_services.ds_edit_dialog import DsEditDialog

FORM_CLASS, _ = uic.loadUiType(
    str(Path(__file__).parent / "user_services_box.ui")
)


class UserServicesBox(QGroupBox, FORM_CLASS):
    """
    Widget for managing user-defined map services in QuickMapServices.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the user services management box.

        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        """
        super(UserServicesBox, self).__init__(parent)
        self.setupUi(self)

        self.feel_list()

        self.lstServices.currentItemChanged.connect(self.on_sel_changed)
        self.lstServices.itemDoubleClicked.connect(self.on_edit)
        self.btnEdit.clicked.connect(self.on_edit)
        self.btnAdd.clicked.connect(self.on_add)
        self.btnDelete.clicked.connect(self.on_delete)
        self.btnCopy.clicked.connect(self.on_copy)

        self.btnAdd.setIcon(QgsApplication.getThemeIcon("symbologyAdd.svg"))
        self.btnEdit.setIcon(QgsApplication.getThemeIcon("symbologyEdit.svg"))
        self.btnDelete.setIcon(
            QgsApplication.getThemeIcon("symbologyRemove.svg")
        )
        self.btnCopy.setIcon(
            QgsApplication.getThemeIcon("mActionEditCopy.svg")
        )

        self.ds_model = DSManagerModel()

    def feel_list(self):
        self.lstServices.clear()
        ds_list = DataSourcesList(USER_DS_PATHS)
        for ds in ds_list.data_sources.values():
            item = QListWidgetItem(ds.action.icon(), ds.action.text())
            item.setData(Qt.ItemDataRole.UserRole, ds)
            self.lstServices.addItem(item)

    def on_sel_changed(self, curr, prev):
        has_sel = curr is not None
        self.btnEdit.setEnabled(has_sel)
        self.btnDelete.setEnabled(has_sel)

    def on_add(self):
        edit_dialog = DsEditDialog()
        edit_dialog.setWindowTitle(self.tr("Create service"))
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            self.feel_list()
            self.ds_model.resetModel()

    def on_edit(self):
        item = self.lstServices.currentItem().data(Qt.ItemDataRole.UserRole)
        edit_dialog = DsEditDialog()
        edit_dialog.setWindowTitle(self.tr("Edit service"))
        edit_dialog.set_ds_info(item)
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            self.feel_list()
            self.ds_model.resetModel()

    def on_delete(self):
        """
        Delete the currently selected user service after confirmation.
        """
        res = QMessageBox.question(
            None,
            self.tr("Delete service"),
            self.tr("Delete selected service?"),
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            ds_info = self.lstServices.currentItem().data(
                Qt.ItemDataRole.UserRole
            )
            dir_path = str(Path(ds_info.file_path).parent)
            shutil.rmtree(dir_path, True)
            self.feel_list()
            self.ds_model.resetModel()

    def on_copy(self):
        self.ds_model.sort(DSManagerModel.COLUMN_GROUP_DS)

        select_data_sources_dialog = QDialog(self)
        select_data_sources_dialog.resize(400, 400)
        select_data_sources_dialog.setWindowTitle(
            self.tr("Choose source service")
        )
        layout = QVBoxLayout(select_data_sources_dialog)
        select_data_sources_dialog.setLayout(layout)

        list_view = QTreeView(self)
        layout.addWidget(list_view)
        list_view.setModel(self.ds_model)
        # list_view.expandAll()
        list_view.setColumnHidden(DSManagerModel.COLUMN_VISIBILITY, True)
        list_view.setAlternatingRowColors(True)

        if hasattr(list_view.header(), "setResizeMode"):
            # Qt4
            list_view.header().setResizeMode(
                DSManagerModel.COLUMN_GROUP_DS,
                QHeaderView.ResizeMode.ResizeToContents,
            )
        else:
            # Qt5
            list_view.header().setSectionResizeMode(
                DSManagerModel.COLUMN_GROUP_DS,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        list_view.clicked.connect(
            lambda index: select_data_sources_dialog.accept()
            if not self.ds_model.isGroup(index)
            and index.column() == DSManagerModel.COLUMN_GROUP_DS
            else None
        )

        if select_data_sources_dialog.exec() == QDialog.DialogCode.Accepted:
            data_source = self.ds_model.data(
                list_view.currentIndex(), Qt.ItemDataRole.UserRole
            )
            data_source.id += "_copy"
            edit_dialog = DsEditDialog()
            edit_dialog.setWindowTitle(self.tr("Create service from existing"))
            edit_dialog.fill_ds_info(data_source)
            if edit_dialog.exec() == QDialog.DialogCode.Accepted:
                self.feel_list()
                self.ds_model.resetModel()
