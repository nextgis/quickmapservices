# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QuickMapServices
                                 A QGIS plugin
 Collection of internet map services
                             -------------------
        begin                : 2014-11-21
        git sha              : $Format:%H$
        copyright            : (C) 2014 by NextGIS
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

import functools

from PyQt4 import QtGui
from PyQt4.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt4.QtGui import QIcon
from plugin_settings import PluginSettings


class ForWorker(QObject):
    nextElement = pyqtSignal(object)
    endList = pyqtSignal()

    def __init__(self, list_for_iterate, time_interval = 10):
        super(ForWorker, self).__init__(None)
        self.__list = list_for_iterate
        self.__time_interval = time_interval

    def run(self):
        for element in self.__list:
            self.nextElement.emit(element)
            self.thread().msleep(self.__time_interval)
        self.endList.emit()

class MyQTableWidgetItem(QtGui.QTableWidgetItem):
    def __lt__(self, other):
        if self.data(Qt.UserRole) < other.data(Qt.UserRole):
            return True
        return False

class DataSourceManager(QtGui.QDialog):
    def __init__(self, ds_list, parent=None):
        super(DataSourceManager, self).__init__(parent)

        self.resize(500, 300)

        self.__ds_hide_id_list = PluginSettings.get_hide_ds_id_list()

        layout = QtGui.QVBoxLayout(self)
        layout.setMargin(0)
        self.setLayout(layout)

        self.__ds_table = QtGui.QTableWidget()
        layout.addWidget(self.__ds_table)

        self.__ds_table.setColumnCount(2)
        self.__ds_table.setHorizontalHeaderLabels([
            self.tr("DS name"),
            self.tr("Visible"),
            # "Source",
        ])

        self.__current_sort_order_4_ds_names = Qt.AscendingOrder
        self.__current_sort_order_4_visible = Qt.AscendingOrder

        self.__ds_table.verticalHeader().hide()
        self.__ds_table.verticalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)

        self.__ds_table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.__ds_table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.__ds_table.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        self.__ds_table.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        self.__ds_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        self.__ds_table.setShowGrid(False)
        self.__ds_table.setAlternatingRowColors(True)
        self.__ds_table.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.__ds_table.setFocusPolicy(Qt.NoFocus)

        self.worker = ForWorker(ds_list)
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.worker.nextElement.connect(self.add_ds_row)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def add_ds_row(self, ds):
        ds_index = self.__ds_table.rowCount()
        self.__ds_table.setRowCount(ds_index + 1)
        self.__ds_table.setItem(
            ds_index,
            0,
            QtGui.QTableWidgetItem(QIcon(ds.icon_path), ds.alias)
        )

        self.cb_widget = QtGui.QWidget()
        cb_widget_layout = QtGui.QVBoxLayout()
        cb_widget_layout.setAlignment(Qt.AlignCenter)
        self.cb_widget.setLayout(cb_widget_layout)
        cb_widget_layout.addSpacing(6)
        
        ds_is_visible = ds.id not in self.__ds_hide_id_list
        cb = QtGui.QCheckBox()
        if ds_is_visible:
            cb.setCheckState(Qt.Checked)
        else:
            cb.setCheckState(Qt.Unchecked)
        cb.stateChanged.connect(
            functools.partial(self.cb_hanged_state, ds.id)
        )
        cb_widget_layout.addWidget(cb)
        self.__ds_table.setCellWidget(ds_index, 1, self.cb_widget)
        cb_item = MyQTableWidgetItem()
        cb_item.setData(Qt.UserRole, int(ds_is_visible))
        self.__ds_table.setItem(
            ds_index,
            1,
            cb_item
        )

        self.__ds_table.sortItems(0, self.__current_sort_order_4_ds_names)

    def cb_hanged_state(self, ds_id, state):
        ds_id_list = PluginSettings.get_hide_ds_id_list()

        if state == Qt.Checked:
            ds_id_list.remove(ds_id)
        elif state == Qt.Unchecked:
            ds_id_list.append(ds_id)

        PluginSettings.set_hide_ds_id_list(ds_id_list)

    def sort_by(self, index):
        print "sort_by: ", index
        if index == 0:
            if self.__current_sort_order_4_ds_names is None:
                self.__current_sort_order_4_ds_names = Qt.AscendingOrder 
            elif self.__current_sort_order_4_ds_names == Qt.AscendingOrder:
                self.__current_sort_order_4_ds_names = Qt.DescendingOrder
            elif self.__current_sort_order_4_ds_names == Qt.DescendingOrder:
                self.__current_sort_order_4_ds_names = Qt.AscendingOrder
            self.__ds_table.sortItems(index, self.__current_sort_order_4_ds_names)

            self.__current_sort_order_4_visible = None
        if index == 1:
            if self.__current_sort_order_4_visible is None:
                self.__current_sort_order_4_visible = Qt.AscendingOrder 
            elif self.__current_sort_order_4_visible == Qt.AscendingOrder:
                self.__current_sort_order_4_visible = Qt.DescendingOrder
            elif self.__current_sort_order_4_visible == Qt.DescendingOrder:
                self.__current_sort_order_4_visible = Qt.AscendingOrder
            self.__ds_table.sortItems(index, self.__current_sort_order_4_visible)

            self.__current_sort_order_4_ds_names = None

        #     target_state = Qt.Checked
        #     if self.__current_sort_order_4_visible is None: 
        #         self.__current_sort_order_4_visible = "checked_first"
        #         target_state = Qt.Checked
        #     elif self.__current_sort_order_4_visible == "checked_first":
        #         self.__current_sort_order_4_visible = "unchecked_first"
        #         target_state = Qt.Unchecked
        #     else:
        #         self.__current_sort_order_4_visible = "checked_first"
        #         target_state = Qt.Checked

        #     count = 0
        #     for row in xrange(0, len(self.__ds_table.rowCount)):
        #         if self.__ds_table.cellWidget(row, 1)

