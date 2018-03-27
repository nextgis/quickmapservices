from __future__ import absolute_import
import os
import sys
import shutil

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QGroupBox, QListWidgetItem, QDialog, QVBoxLayout, QTableView, QHeaderView, QMessageBox

from .groups_list import GroupsList, USER_GROUP_PATHS
from .group_edit_dialog import GroupEditDialog
from .data_sources_model import DSManagerModel
from .compat import get_file_dir

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'user_groups_box.ui'))

plugin_dir = get_file_dir(__file__)

class UserGroupsBox(QGroupBox, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(UserGroupsBox, self).__init__(parent)
        self.setupUi(self)

        self.feel_list()

        self.lstGroups.currentItemChanged.connect(self.on_sel_changed)
        self.lstGroups.itemDoubleClicked.connect(self.on_edit)
        self.btnEdit.clicked.connect(self.on_edit)
        self.btnAdd.clicked.connect(self.on_add)
        self.btnDelete.clicked.connect(self.on_delete)
        self.btnCopy.clicked.connect(self.on_copy)

        self.btnAdd.setIcon(QIcon(plugin_dir + '/icons/plus.svg'))
        self.btnEdit.setIcon(QIcon(plugin_dir + '/icons/compose.svg'))
        self.btnDelete.setIcon(QIcon(plugin_dir + '/icons/trash.svg'))
        self.btnCopy.setIcon(QIcon(plugin_dir + '/icons/copy.svg'))

        self.ds_model = DSManagerModel()

    def feel_list(self):
        self.lstGroups.clear()
        ds_groups = GroupsList(USER_GROUP_PATHS)
        for ds_group in ds_groups.groups.values():
            item = QListWidgetItem(QIcon(ds_group.icon), self.tr(ds_group.alias))
            item.setData(Qt.UserRole, ds_group)
            self.lstGroups.addItem(item)

    def on_sel_changed(self, curr, prev):
        has_sel = curr is not None
        self.btnEdit.setEnabled(has_sel)
        self.btnDelete.setEnabled(has_sel)

    def on_add(self):
        edit_dialog = GroupEditDialog()
        edit_dialog.setWindowTitle(self.tr('Create group'))
        if edit_dialog.exec_() == QDialog.Accepted:
            self.feel_list()
            self.ds_model.resetModel()

    def on_edit(self):
        item = self.lstGroups.currentItem().data(Qt.UserRole)
        edit_dialog = GroupEditDialog()
        edit_dialog.setWindowTitle(self.tr('Edit group'))
        edit_dialog.set_group_info(item)
        if edit_dialog.exec_() == QDialog.Accepted:
            self.feel_list()
            self.ds_model.resetModel()

    def on_delete(self):
        res = QMessageBox.question(None,
                                   self.tr('Delete group'),
                                   self.tr('Delete selected group?'),
                                   QMessageBox.Yes, QMessageBox.No)
        if res == QMessageBox.Yes:
            group_info = self.lstGroups.currentItem().data(Qt.UserRole)
            dir_path = os.path.abspath(os.path.join(group_info.file_path, os.path.pardir))
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
        groups_list_view.setColumnHidden(DSManagerModel.COLUMN_VISIBILITY, True)
        groups_list_view.setSelectionMode(QTableView.NoSelection)
        groups_list_view.setAlternatingRowColors(True)
        groups_list_view.setShowGrid(False)
        if hasattr(groups_list_view.horizontalHeader(), "setResizeMode"):
            # Qt4
            groups_list_view.horizontalHeader().setResizeMode(DSManagerModel.COLUMN_GROUP_DS, QHeaderView.Stretch)
            groups_list_view.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
        else:
            # Qt5
            groups_list_view.horizontalHeader().setSectionResizeMode(DSManagerModel.COLUMN_GROUP_DS, QHeaderView.Stretch)
            groups_list_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        groups_list_view.verticalHeader().hide()
        groups_list_view.clicked.connect(
            lambda index: select_group_dialog.accept() \
                if self.ds_model.isGroup(index) and \
                    index.column() == DSManagerModel.COLUMN_GROUP_DS \
                else None
        )

        if select_group_dialog.exec_() == QDialog.Accepted:
            group_info = self.ds_model.data(groups_list_view.currentIndex(), Qt.UserRole)
            group_info.id += "_copy"
            edit_dialog = GroupEditDialog()
            edit_dialog.setWindowTitle(self.tr('Create group from existing'))
            edit_dialog.fill_group_info(group_info)
            if edit_dialog.exec_() == QDialog.Accepted:
                self.feel_list()
                self.ds_model.resetModel()
