from __future__ import absolute_import
import os
import shutil
import codecs
from os import path

from qgis.PyQt import uic
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from . import extra_sources
from .fixed_config_parser import FixedConfigParser
from .groups_list import GroupsList
from .gui.line_edit_color_validator import LineEditColorValidator
from .plugin_settings import PluginSettings
from .compat2qgis import getOpenFileName

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'group_edit_dialog.ui'))


def is_same(file1, file2):
    return os.path.normcase(os.path.normpath(file1)) == \
                os.path.normcase(os.path.normpath(file2))


class GroupEditDialog(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(GroupEditDialog, self).__init__(parent)
        self.setupUi(self)

        # init icon selector
        # self.txtIcon.set_dialog_ext(self.tr('All icon files (*.ico *.jpg *.jpeg *.png *.svg);;All files (*.*)'))
        # self.txtIcon.set_dialog_title(self.tr('Select icon for group'))
        self.iconChooseButton.clicked.connect(self.choose_icon)

        # validators
        self.id_validator = LineEditColorValidator(self.txtId, '^[A-Za-z0-9_]+$', error_tooltip=self.tr('Any text'))
        self.alias_validator = LineEditColorValidator(self.txtAlias, '^[A-Za-z0-9_ ]+$', error_tooltip=self.tr('Any text'))

        # vars
        self.group_info = None
        self.init_with_existing = False
        
        self.set_icon(
            os.path.join(
                os.path.dirname(__file__),
                'icons',
                'mapservices.png'
            )
        )

    def set_group_info(self, group_info):
        self.group_info = group_info
        self.init_with_existing = True
        # feel fields
        self.txtId.setText(self.group_info.id)
        self.txtAlias.setText(self.group_info.alias)
        # self.txtIcon.set_path(self.group_info.icon)
        self.set_icon(self.group_info.icon)

    def fill_group_info(self, group_info):
        self.group_info = group_info
        self.init_with_existing = False
        # feel fields
        self.txtId.setText(self.group_info.id)
        self.txtAlias.setText(self.group_info.alias)
        # self.txtIcon.set_path(self.group_info.icon)
        self.set_icon(self.group_info.icon)

    def choose_icon(self):
        print(PluginSettings.get_default_user_icon_path())
        icon_path = getOpenFileName(
            self,
            self.tr('Select icon for group'),
            PluginSettings.get_default_user_icon_path(),
            self.tr('All icon files (*.ico *.jpg *.jpeg *.png *.svg);;All files (*.*)')
        )

        print(icon_path)
        if icon_path != "":
            PluginSettings.set_default_user_icon_path(icon_path)
            self.set_icon(icon_path)

    def set_icon(self, icon_path):
        self.__group_icon = icon_path
        self.iconPreview.setPixmap(
            QPixmap(self.__group_icon)
        )

    def accept(self):
        if self.init_with_existing:
            res = self.save_existing()
        else:
            res = self.create_new()
        if res:
            super(GroupEditDialog, self).accept()

    def validate(self, group_id, group_alias, group_icon):
        checks = [
            (group_id, self.tr('Please, enter group id')),
            (group_alias, self.tr('Please, enter group alias')),
            (group_icon, self.tr('Please, select icon for group')),
        ]

        for val, comment in checks:
            if not val:
                QMessageBox.critical(self, self.tr('Error on save group'), comment)
                return False

        checks_correct = [
            (self.id_validator, 'Please, enter correct value for group id'),
            (self.alias_validator, 'Please, enter correct value for group alias'),
        ]

        for val, comment in checks_correct:
            if not val.is_valid():
                QMessageBox.critical(self, self.tr('Error on save group'), self.tr(comment))
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
        # group_icon = self.txtIcon.get_path()
        group_icon = self.__group_icon

        if not self.validate(group_id, group_alias, group_icon):
            return False

        if group_id != self.group_info.id and not self.check_existing_id(group_id):
            return False

        if group_id == self.group_info.id and \
           group_alias == self.group_info.alias and \
           is_same(group_icon, self.group_info.icon):
            return True

        # replace icon if need
        if not is_same(group_icon, self.group_info.icon):
            os.remove(self.group_info.icon)

            dir_path = os.path.dirname(self.group_info.file_path)

            ico_file_name = path.basename(group_icon)
            ico_path = path.join(dir_path, ico_file_name)

            shutil.copy(group_icon, ico_path)

        # write config
        config = FixedConfigParser()

        config.add_section('general')
        config.add_section('ui')
        config.set('general', 'id', group_id)
        config.set('ui', 'alias', group_alias)
        config.set('ui', 'icon', path.basename(group_icon))

        with codecs.open(self.group_info.file_path, 'w', 'utf-8') as configfile:
            config.write(configfile)

        return True

    def create_new(self):
        group_id = self.txtId.text()
        group_alias = self.txtAlias.text()
        # group_icon = self.txtIcon.get_path()
        group_icon = self.__group_icon

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
        config = FixedConfigParser()

        config.add_section('general')
        config.add_section('ui')
        config.set('general', 'id', group_id)
        config.set('ui', 'alias', group_alias)
        config.set('ui', 'icon', ico_file_name)

        with codecs.open(ini_path, 'w', 'utf-8') as configfile:
            config.write(configfile)

        return True
