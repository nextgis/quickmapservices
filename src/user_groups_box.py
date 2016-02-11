import os
import shutil

from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QGroupBox, QListWidgetItem, QDialog, QMessageBox, QIcon

from groups_list import GroupsList, USER_GROUP_PATHS
from group_edit_dialog import GroupEditDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'user_groups_box.ui'))

import resources_rc

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

        self.btnAdd.setIcon(QIcon(":/plugins/QuickMapServices/icons/plus.svg"))
        self.btnEdit.setIcon(QIcon(":/plugins/QuickMapServices/icons/compose.svg"))
        self.btnDelete.setIcon(QIcon(":/plugins/QuickMapServices/icons/trash.svg"))

    def feel_list(self):
        self.lstGroups.clear()
        ds_groups = GroupsList(USER_GROUP_PATHS)
        for ds_group in ds_groups.groups.itervalues():
            item = QListWidgetItem(QIcon(ds_group.icon), self.tr(ds_group.alias))
            item.setData(Qt.UserRole, ds_group)
            self.lstGroups.addItem(item)

    def on_sel_changed(self, curr, prev):
        has_sel = curr is not None
        self.btnEdit.setEnabled(has_sel)
        self.btnDelete.setEnabled(has_sel)

    def on_add(self):
        edit_dialog = GroupEditDialog()
        edit_dialog.setWindowTitle(self.tr('Create new user group'))
        if edit_dialog.exec_() == QDialog.Accepted:
            self.feel_list()

    def on_edit(self):
        item = self.lstGroups.currentItem().data(Qt.UserRole)
        edit_dialog = GroupEditDialog()
        edit_dialog.setWindowTitle(self.tr('Edit user group'))
        edit_dialog.set_group_info(item)
        if edit_dialog.exec_() == QDialog.Accepted:
            self.feel_list()


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
