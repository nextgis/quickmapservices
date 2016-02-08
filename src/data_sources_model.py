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
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, QAbstractItemModel, QModelIndex
from PyQt4.QtGui import QIcon
from plugin_settings import PluginSettings


class DSManagerModel(QAbstractItemModel):
    def __init__(self, dsList, parent=None):
        super(DSManagerModel, self).__init__(parent)
        self.rootItem = QtGui.QTreeWidgetItem(
            [
                self.tr("Group/DS"),
                self.tr("Visible")
            ]
        )
        self.__setupModelData(dsList)

    def __setupModelData(self, dsList):
        groupsItems = []
        groups = []
        for ds in dsList:
            if ds.group in groups:
                group_item = groupsItems[groups.index(ds.group)]
            else:
                group_item = QtGui.QTreeWidgetItem([ds.group])
                group_item.setCheckState(1, Qt.Unchecked)
                groups.append(ds.group)
                groupsItems.append(group_item)
                self.rootItem.addChild(group_item)
                

            ds_item = QtGui.QTreeWidgetItem([ds.alias])
            ds_item.setData(0, Qt.UserRole, ds.id)
            ds_item.setIcon(0, QIcon(ds.icon_path))

            ds_check_state = Qt.Checked
            if ds.id in PluginSettings.get_hide_ds_id_list():
                ds_check_state = Qt.Unchecked
            ds_item.setCheckState(1, ds_check_state)

            if group_item.childCount() != 0 and group_item.checkState(1) != ds_check_state:
                group_item.setCheckState(1, Qt.PartiallyChecked)
            else:
                group_item.setCheckState(1, ds_check_state)

            group_item.addChild(
                ds_item
            )

        self.sort(0)

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        else:
            item = index.internalPointer()

        if role == Qt.CheckStateRole:
            item.setData(1, role, value)

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

        if role not in [Qt.DisplayRole, Qt.CheckStateRole, Qt.DecorationRole]:
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
        # if parent.column() > 0:
        #     return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def sort(self, column, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        if column == 0:
            role = Qt.DisplayRole
        elif column == 1:
            role = Qt.CheckStateRole

        if order == Qt.AscendingOrder:
            compareFunc = lambda a,b: True if cmp(a, b) < 0 else False
        else:
            compareFunc = lambda a,b: True if cmp(a, b) > 0 else False

        for groupIndexI in range(0, self.rootItem.childCount()):
            for groupIndexJ in range(0, groupIndexI):
                groupItemI = self.rootItem.child(groupIndexI)
                groupItemJ = self.rootItem.child(groupIndexJ)
                if compareFunc(groupItemI.data(column, role), groupItemJ.data(column, role)):
                    self.rootItem.insertChild(groupIndexJ, self.rootItem.takeChild(groupIndexI))
                    break

        self.layoutChanged.emit()

    def checkAll(self):
        print "checkAll"
        for row in range(0, self.rootItem.childCount()):
            groupItem = self.rootItem.child(row)
            groupIndex = self.createIndex(row, 1, groupItem)
            self.setData(groupIndex, Qt.Checked, Qt.CheckStateRole)

    def uncheckAll(self):
        print "uncheckAll"
        for row in range(0, self.rootItem.childCount()):
            groupItem = self.rootItem.child(row)
            groupIndex = self.createIndex(row, 1, groupItem)
            self.setData(groupIndex, Qt.Unchecked, Qt.CheckStateRole)

    def saveSettings(self):
        hideDSidList = []
        for groupIndex in range(0, self.rootItem.childCount()):
            groupItem = self.rootItem.child(groupIndex)
            for dsIndex in range(0, groupItem.childCount()):
                dsItem = groupItem.child(dsIndex)
                if dsItem.checkState(1) == Qt.Unchecked:
                    hideDSidList.append(dsItem.data(0, Qt.UserRole))
        PluginSettings.set_hide_ds_id_list(hideDSidList)
