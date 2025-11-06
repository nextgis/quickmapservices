import shutil
from pathlib import Path
from typing import Optional

from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHeaderView,
    QListWidgetItem,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from quick_map_services.data_sources_model import DSManagerModel
from quick_map_services.group_edit_dialog import GroupEditDialog
from quick_map_services.groups_list import USER_GROUP_PATHS, GroupsList

FORM_CLASS, _ = uic.loadUiType(
    str(Path(__file__).parent / "user_groups_box.ui")
)


class UserGroupsBox(QGroupBox, FORM_CLASS):
    """
    Widget for managing user-defined service groups in QuickMapServices.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the user groups management box.

        :param parent: Optional parent widget.
        :type parent: Optional[QWidget]
        """
        super(UserGroupsBox, self).__init__(parent)
        self.setupUi(self)

        self.feel_list()

        self.lstGroups.currentItemChanged.connect(self.on_sel_changed)
        self.lstGroups.itemDoubleClicked.connect(self.on_edit)
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
        self.lstGroups.clear()
        ds_groups = GroupsList(USER_GROUP_PATHS)
        for ds_group in ds_groups.groups.values():
            item = QListWidgetItem(
                QIcon(ds_group.icon), self.tr(ds_group.alias)
            )
            item.setData(Qt.ItemDataRole.UserRole, ds_group)
            self.lstGroups.addItem(item)

    def on_sel_changed(self, curr, prev):
        has_sel = curr is not None
        self.btnEdit.setEnabled(has_sel)
        self.btnDelete.setEnabled(has_sel)

    def on_add(self):
        edit_dialog = GroupEditDialog()
        edit_dialog.setWindowTitle(self.tr("Create group"))
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            self.feel_list()
            self.ds_model.resetModel()

    def on_edit(self):
        item = self.lstGroups.currentItem().data(Qt.ItemDataRole.UserRole)
        edit_dialog = GroupEditDialog()
        edit_dialog.setWindowTitle(self.tr("Edit group"))
        edit_dialog.set_group_info(item)
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            self.feel_list()
            self.ds_model.resetModel()

    def on_delete(self) -> None:
        """
        Delete the currently selected user group after confirmation.
        """
        res = QMessageBox.question(
            None,
            self.tr("Delete group"),
            self.tr("Delete selected group?"),
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            group_info = self.lstGroups.currentItem().data(
                Qt.ItemDataRole.UserRole
            )
            dir_path = str(Path(group_info.file_path).parent)
            shutil.rmtree(dir_path, True)
            self.feel_list()
            self.ds_model.resetModel()

    def on_copy(self):
        select_group_dialog = QDialog(self)
        select_group_dialog.resize(300, 400)
        select_group_dialog.setWindowTitle(self.tr("Choose source group"))
        layout = QVBoxLayout(select_group_dialog)
        select_group_dialog.setLayout(layout)

        groups_list_view = QTableView(self)
        layout.addWidget(groups_list_view)
        groups_list_view.setModel(self.ds_model)
        groups_list_view.setColumnHidden(
            DSManagerModel.COLUMN_VISIBILITY, True
        )
        groups_list_view.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        groups_list_view.setAlternatingRowColors(True)
        groups_list_view.setShowGrid(False)
        if hasattr(groups_list_view.horizontalHeader(), "setResizeMode"):
            # Qt4
            groups_list_view.horizontalHeader().setResizeMode(
                DSManagerModel.COLUMN_GROUP_DS, QHeaderView.ResizeMode.Stretch
            )
            groups_list_view.verticalHeader().setResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
        else:
            # Qt5
            groups_list_view.horizontalHeader().setSectionResizeMode(
                DSManagerModel.COLUMN_GROUP_DS, QHeaderView.ResizeMode.Stretch
            )
            groups_list_view.verticalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )

        groups_list_view.verticalHeader().hide()
        groups_list_view.clicked.connect(
            lambda index: select_group_dialog.accept()
            if self.ds_model.isGroup(index)
            and index.column() == DSManagerModel.COLUMN_GROUP_DS
            else None
        )

        if select_group_dialog.exec() == QDialog.DialogCode.Accepted:
            group_info = self.ds_model.data(
                groups_list_view.currentIndex(), Qt.ItemDataRole.UserRole
            )
            group_info.id += "_copy"
            edit_dialog = GroupEditDialog()
            edit_dialog.setWindowTitle(self.tr("Create group from existing"))
            edit_dialog.fill_group_info(group_info)
            if edit_dialog.exec() == QDialog.DialogCode.Accepted:
                self.feel_list()
                self.ds_model.resetModel()
