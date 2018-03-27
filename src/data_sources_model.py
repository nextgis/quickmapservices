# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QuickMapServices
                                 A QGIS plugin
 Collection of internet map services
                             -------------------
        begin                : 2014-11-21
        git sha              : $Format:%H$
        copyright            : (C) 2016 by NextGIS
        email                : info@nextgis.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import absolute_import
# from data_source_info import DataSourceCategory
# from group_info import 
from .data_sources_list import DataSourcesList
from .groups_list import GroupsList

from qgis.PyQt.QtCore import Qt, QAbstractItemModel, QModelIndex
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QTreeWidgetItem
from .plugin_settings import PluginSettings

from .singleton import QSingleton


class DSManagerModel(QAbstractItemModel):
    __metaclass__ = QSingleton

    COLUMN_GROUP_DS = 0
    COLUMN_VISIBILITY = 1
    COLUMN_SOURCE = 2

    # instance = None

    # @classmethod
    # def getInstance(cls):
    #     if cls.instance

    def __init__(self, parent=None):
        super(DSManagerModel, self).__init__(parent)

        self.columnNames = []
        self.columnNames.insert(self.COLUMN_GROUP_DS, self.tr("Group/DS"))
        self.columnNames.insert(self.COLUMN_VISIBILITY, self.tr("Visible"))
        self.columnNames.insert(self.COLUMN_SOURCE, self.tr("Source"))

        self.rootItem = QTreeWidgetItem(self.columnNames)
        self.__setupModelData()

    def resetModel(self):
        self.beginResetModel()
        self.__clear()
        self.__setupModelData()
        self.endResetModel()
        self.modelReset.emit()

    def __clear(self):
        for groupIndex in range(self.rootItem.childCount() - 1, -1, -1):
            groupItem = self.rootItem.child(groupIndex)
            for dsIndex in range(groupItem.childCount() - 1, -1, -1):
                dsItem = groupItem.child(dsIndex)
                groupItem.removeChild(dsItem)
            self.rootItem.removeChild(groupItem)

    def __setupModelData(self):
        dsList = DataSourcesList().data_sources.values()
        groupInfoList = GroupsList().groups
        groupsItems = []
        groups = []
        for ds in dsList:
            if ds.group in groups:
                group_item = groupsItems[groups.index(ds.group)]
            else:
                group_item = QTreeWidgetItem()
                group_item.setData(self.COLUMN_GROUP_DS, Qt.DisplayRole, ds.group)
                group_item.setData(self.COLUMN_VISIBILITY, Qt.DisplayRole, "")
                group_item.setData(self.COLUMN_SOURCE, Qt.DisplayRole, ds.category)
                group_item.setCheckState(self.COLUMN_VISIBILITY, Qt.Unchecked)

                groupInfo = groupInfoList.get(ds.group)
                if groupInfo is not None:
                    group_item.setIcon(self.COLUMN_GROUP_DS, QIcon(groupInfo.icon))
                else:
                    group_item.setData(self.COLUMN_GROUP_DS, Qt.DisplayRole, ds.group + " (%s!)" % self.tr("group not found"))
                group_item.setData(self.COLUMN_GROUP_DS, Qt.UserRole, groupInfo)

                groups.append(ds.group)
                groupsItems.append(group_item)
                self.rootItem.addChild(group_item)

            ds_item = QTreeWidgetItem()
            ds_item.setData(self.COLUMN_GROUP_DS, Qt.DisplayRole, ds.alias)
            ds_item.setIcon(self.COLUMN_GROUP_DS, QIcon(ds.icon_path))
            ds_item.setData(self.COLUMN_GROUP_DS, Qt.UserRole, ds)
            ds_item.setData(self.COLUMN_VISIBILITY, Qt.DisplayRole, "")
            ds_item.setData(self.COLUMN_SOURCE, Qt.DisplayRole, ds.category)

            ds_check_state = Qt.Checked
            if ds.id in PluginSettings.get_hide_ds_id_list():
                ds_check_state = Qt.Unchecked
            ds_item.setCheckState(self.COLUMN_VISIBILITY, ds_check_state)

            if group_item.childCount() != 0 and group_item.checkState(1) != ds_check_state:
                group_item.setCheckState(self.COLUMN_VISIBILITY, Qt.PartiallyChecked)
            else:
                group_item.setCheckState(self.COLUMN_VISIBILITY, ds_check_state)

            group_item.addChild(
                ds_item
            )

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        else:
            item = index.internalPointer()

        if role == Qt.CheckStateRole:
            item.setData(self.COLUMN_VISIBILITY, role, value)

            self.dataChanged.emit(
                index,
                index
            )

            self.updateChecks(index, value)
        return True

    def updateChecks(self, index, checkState):
        if self.hasChildren(index):
            for row in range(0, self.rowCount(index)):
                childItem = index.internalPointer().child(row)
                childItem.setCheckState(index.column(), checkState)

            self.dataChanged.emit(
                self.index(0, index.column(), index),
                self.index(row, index.column(), index)
            )
        else:
            parentIndex = self.parent(index)
            parentItem = parentIndex.internalPointer()

            diff = False
            for row in range(0, self.rowCount(parentIndex)):
                childItem = parentItem.child(row)
                if childItem.checkState(index.column()) != checkState:
                    diff = True
                    break

            if diff:
                parentItem.setCheckState(index.column(), Qt.PartiallyChecked)
            else:
                parentItem.setCheckState(index.column(), checkState)

            self.dataChanged.emit(
                parentIndex,
                parentIndex
            )

    def columnCount(self, parent):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index, role):
        if not index.isValid():
            return None

        if role not in [Qt.DisplayRole, Qt.CheckStateRole, Qt.DecorationRole, Qt.UserRole]:
            return None

        item = index.internalPointer()
        return item.data(index.column(), role)

    def flags(self, index):
        if not index.isValid():
            item = self.rootItem
        else:
            item = index.internalPointer()

        return item.flags()

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section, Qt.DisplayRole)

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.parent().indexOfChild(parentItem), index.column(), parentItem)

    def rowCount(self, parent):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def sort(self, column, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        if column == self.COLUMN_VISIBILITY:
            role = Qt.CheckStateRole
        else:
            role = Qt.DisplayRole

        if order == Qt.AscendingOrder:
            # compareFunc = lambda a, b: True if cmp(a, b) < 0 else False
            compareFunc = lambda a, b: a < b # need to check
        else:
            # compareFunc = lambda a, b: True if cmp(a, b) > 0 else False
            compareFunc = lambda a, b: a >= b # need to check

        for groupIndexI in range(0, self.rootItem.childCount()):
            for groupIndexJ in range(0, groupIndexI):
                groupItemI = self.rootItem.child(groupIndexI)
                groupItemJ = self.rootItem.child(groupIndexJ)
                if compareFunc(groupItemI.data(column, role), groupItemJ.data(column, role)):
                    self.rootItem.insertChild(groupIndexJ, self.rootItem.takeChild(groupIndexI))
                    break

        self.layoutChanged.emit()

    def checkAll(self):
        for row in range(0, self.rootItem.childCount()):
            groupItem = self.rootItem.child(row)
            groupIndex = self.createIndex(row, self.COLUMN_VISIBILITY, groupItem)
            self.setData(groupIndex, Qt.Checked, Qt.CheckStateRole)

    def uncheckAll(self):
        for row in range(0, self.rootItem.childCount()):
            groupItem = self.rootItem.child(row)
            groupIndex = self.createIndex(row, self.COLUMN_VISIBILITY, groupItem)
            self.setData(groupIndex, Qt.Unchecked, Qt.CheckStateRole)

    def saveSettings(self):
        hideDSidList = []
        for groupIndex in range(0, self.rootItem.childCount()):
            groupItem = self.rootItem.child(groupIndex)
            for dsIndex in range(0, groupItem.childCount()):
                dsItem = groupItem.child(dsIndex)
                if dsItem.checkState(self.COLUMN_VISIBILITY) == Qt.Unchecked:
                    hideDSidList.append(dsItem.data(self.COLUMN_GROUP_DS, Qt.UserRole).id)
        PluginSettings.set_hide_ds_id_list(hideDSidList)

    def isGroup(self, index):
        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return True

        return False
