import codecs
import os
import ConfigParser
import shutil

from PyQt4 import uic
from PyQt4.QtGui import QDialog, QMessageBox
from os import path

import extra_sources
from groups_list import GroupsList
from .gui.line_edit_color_validator import LineEditColorValidator

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'group_edit_dialog.ui'))

class GroupEditDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(GroupEditDialog, self).__init__(parent)
        self.setupUi(self)

        # init icon selector
        self.txtIcon.set_dialog_ext(self.tr('Icons (*.ico);;Jpeg (*.jpg);;Png (*.png);;All files (*.*)'))
        self.txtIcon.set_dialog_title(self.tr('Select icon for group'))

        # validators
        self.id_validator = LineEditColorValidator(self.txtId, '^[A-Za-z0-9_]+$', error_tooltip=self.tr('Any text'))
        self.alias_validator = LineEditColorValidator(self.txtAlias, '^.+$', error_tooltip=self.tr('Any text'))

        # vars
        self.group_info = None
        self.init_with_existing = False


    def set_group_info(self, group_info):
        self.group_info = group_info
        self.init_with_existing = True
        # feel fields
        self.txtId.setText(self.group_info.id)
        self.txtAlias.setText(self.group_info.alias)
        self.txtIcon.set_path(self.group_info.icon)

    def accept(self):
        if self.init_with_existing:
            res = self.save_existing()
        else:
            res = self.create_new()
        if res:
            super(GroupEditDialog, self).accept()

    def validate(self, group_id, group_alias, group_icon):
        if not group_id:
            QMessageBox.critical(self, self.tr('Error on save group'), self.tr('Please, enter group id'))
            return False
        if not group_alias:
            QMessageBox.critical(self, self.tr('Error on save group'), self.tr('Please, enter group alias!'))
            return False
        if not group_icon:
            QMessageBox.critical(self, self.tr('Error on save group'), self.tr('Please, select icon for group!'))
            return False
        return True

    def check_existing_id(self, group_id):
        gl = GroupsList()
        if group_id in gl.groups.keys():
            QMessageBox.critical(self, self.tr('Error on save group'),
                                 self.tr('Group with such id already exists! Select new id for group!'))
            return False
        return True

    def save_existing(self):
        group_id = self.txtId.text()
        group_alias = self.txtAlias.text()
        group_icon = self.txtIcon.get_path()

        if not self.validate(group_id, group_alias, group_icon):
            return False

        if group_id != self.group_info.id and not self.check_existing_id(group_id):
            return False

        if group_id == self.group_info.id and \
           group_alias == self.group_info.alias and \
           group_icon == self.group_info.icon:
            return True

        # replace icon if need
        if group_icon != self.group_info.icon:
            os.remove(self.group_info.icon)

            dir_path = os.path.abspath(os.path.join(self.group_info.file_path, os.path.pardir))

            ico_file_name = path.basename(group_icon)
            ico_path = path.join(dir_path, ico_file_name)

            shutil.copy(group_icon, ico_path)


        # write config
        config = ConfigParser.RawConfigParser()

        config.add_section('general')
        config.add_section('ui')
        config.set('general', 'id', group_id)
        config.set('ui', 'alias', group_alias)
        config.set('ui', 'icon', path.basename(group_icon))

        with codecs.open(self.group_info.file_path, 'wt', 'utf-8') as configfile:
            config.write(configfile)

        return True

    def create_new(self):
        group_id = self.txtId.text()
        group_alias = self.txtAlias.text()
        group_icon = self.txtIcon.get_path()

        if not self.validate(group_id, group_alias, group_icon):
            return False

        if not self.check_existing_id(group_id):
            return False

        # set paths
        dir_path = path.join(extra_sources.USER_DIR_PATH, extra_sources.GROUPS_DIR_NAME, group_id)

        if path.exists(dir_path):
            salt = 0
            while path.exists(dir_path + str(salt)):
                salt += 1
            dir_path += str(salt)

        ini_path = path.join(dir_path, 'metadata.ini')

        ico_file_name = path.basename(group_icon)
        ico_path = path.join(dir_path, ico_file_name)

        # create dir
        os.mkdir(dir_path)

        # copy icon
        shutil.copy(group_icon, ico_path)

        # write config
        config = ConfigParser.RawConfigParser()

        config.add_section('general')
        config.add_section('ui')
        config.set('general', 'id', group_id)
        config.set('ui', 'alias', group_alias)
        config.set('ui', 'icon', ico_file_name)

        with codecs.open(ini_path, 'wt', 'utf-8') as configfile:
            config.write(configfile)

        return True



