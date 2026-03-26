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

from typing import Any, Dict, List, Optional, Tuple

from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QTreeWidgetItem, QWidget

from quick_map_services.core import utils
from quick_map_services.core.settings import QmsSettings
from quick_map_services.data_source_info import DataSourceInfo
from quick_map_services.data_sources_list import DataSourcesList
from quick_map_services.group_info import GroupInfo
from quick_map_services.groups_list import GroupsList
from quick_map_services.singleton import QSingleton


class DSManagerModel(QAbstractItemModel):
    """
    Model representing grouped data sources in a tree structure.

    The model is used in QMS settings dialog to manage visibility of
    data sources grouped by their categories.
    """

    __metaclass__ = QSingleton

    COLUMN_GROUP_DS = 0
    COLUMN_VISIBILITY = 1
    COLUMN_SOURCE = 2

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the model.

        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)

        self.column_names = []
        self.column_names.insert(self.COLUMN_GROUP_DS, self.tr("Group/DS"))
        self.column_names.insert(self.COLUMN_VISIBILITY, self.tr("Visible"))
        self.column_names.insert(self.COLUMN_SOURCE, self.tr("Source"))

        self.root_item = QTreeWidgetItem(self.column_names)
        self._setup_model_data()

    def _reset_model(self) -> None:
        """
        Reset model content and rebuild tree.

        :return: None
        """
        self.beginResetModel()
        self._clear()
        self._setup_model_data()
        self.endResetModel()
        self.modelReset.emit()

    def _clear(self) -> None:
        """
        Remove all children from root item.

        :return: None
        """
        for group_index in range(self.root_item.childCount() - 1, -1, -1):
            group_item = self.root_item.child(group_index)
            for data_source_index in range(
                group_item.childCount() - 1, -1, -1
            ):
                data_source_item = group_item.child(data_source_index)
                group_item.removeChild(data_source_item)
            self.root_item.removeChild(group_item)

    def _setup_model_data(self) -> None:
        """
        Populate the tree model with available data sources and groups.

        :return: None
        """
        data_sources: List[DataSourceInfo] = list(
            DataSourcesList().data_sources.values()
        )
        group_info_map: Dict[str, GroupInfo] = GroupsList().groups

        groups = utils.collect_groups(data_sources)

        self._build_tree(
            groups,
            group_info_map,
        )

    def setData(
        self, index: QModelIndex, value: Any, role: Qt.ItemDataRole
    ) -> bool:
        """
        Set data for a model index.

        :param index: Model index.
        :param value: Value to set.
        :param role: Qt role.

        :return: Success flag.
        """
        if not index.isValid():
            return False

        item = index.internalPointer()

        if role == Qt.ItemDataRole.CheckStateRole:
            item.setData(self.COLUMN_VISIBILITY, role, value)
            self.dataChanged.emit(index, index)
            self._update_checks(index, value)

        return True

    def _update_checks(
        self, index: QModelIndex, check_state: Qt.CheckState
    ) -> None:
        """
        Update check states for children or parent.

        :param index: Model index.
        :param check_state: New check state.

        :return: None
        """
        if self.hasChildren(index):
            for row in range(0, self.rowCount(index)):
                child_item = index.internalPointer().child(row)
                child_item.setCheckState(
                    index.column(), Qt.CheckState(check_state)
                )

            self.dataChanged.emit(
                self.index(0, index.column(), index),
                self.index(row, index.column(), index),
            )
        else:
            parent_index = self.parent(index)
            parent_item = parent_index.internalPointer()

            diff = False
            for row in range(0, self.rowCount(parent_index)):
                child_item = parent_item.child(row)
                if child_item.checkState(index.column()) != check_state:
                    diff = True
                    break

            if diff:
                parent_item.setCheckState(
                    index.column(), Qt.CheckState.PartiallyChecked
                )
            else:
                parent_item.setCheckState(
                    index.column(), Qt.CheckState(check_state)
                )

            self.dataChanged.emit(parent_index, parent_index)

    def columnCount(self, parent: QModelIndex) -> int:
        """
        Return number of columns.

        :param parent: Parent index.

        :return: Column count.
        """
        if parent.isValid():
            return parent.internalPointer().columnCount()

        return self.root_item.columnCount()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Any:
        """
        Return data for index and role.

        :param index: Model index.
        :param role: Qt role.

        :return: Data value.
        """
        if not index.isValid():
            return None

        if role not in [
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.CheckStateRole,
            Qt.ItemDataRole.DecorationRole,
            Qt.ItemDataRole.UserRole,
        ]:
            return None

        item = index.internalPointer()
        return item.data(index.column(), role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """
        Return item flags.

        :param index: Model index.

        :return: Flags.
        """
        if not index.isValid():
            return self.root_item.flags()

        return index.internalPointer().flags()

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ) -> Any:
        """
        Return header data.

        :param section: Column index.
        :param orientation: Orientation.
        :param role: Qt role.

        :return: Header value.
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.root_item.data(section, Qt.ItemDataRole.DisplayRole)

        return None

    def index(self, row: int, column: int, parent: QModelIndex) -> QModelIndex:
        """
        Create model index.

        :param row: Row index.
        :param column: Column index.
        :param parent: Parent index.

        :return: Model index.
        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = (
            self.root_item
            if not parent.isValid()
            else parent.internalPointer()
        )

        child_item = parent_item.child(row)

        return (
            self.createIndex(row, column, child_item)
            if child_item
            else QModelIndex()
        )

    def parent(self, index: QModelIndex) -> QModelIndex:
        """
        Return parent index.

        :param index: Model index.

        :return: Parent index.
        """
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()
        if parent_item == self.root_item:
            return QModelIndex()

        return self.createIndex(
            parent_item.parent().indexOfChild(parent_item),
            index.column(),
            parent_item,
        )

    def rowCount(self, parent: QModelIndex) -> int:
        """
        Return number of rows.

        :param parent: Parent index.

        :return: Row count.
        """
        parent_item = (
            self.root_item
            if not parent.isValid()
            else parent.internalPointer()
        )

        return parent_item.childCount()

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """
        Sort top-level groups.

        :param column: Column index.
        :param order: Sort order.

        :return: None
        """
        self.layoutAboutToBeChanged.emit()

        role = (
            Qt.ItemDataRole.CheckStateRole
            if column == self.COLUMN_VISIBILITY
            else Qt.ItemDataRole.DisplayRole
        )

        def sort_key(item: QTreeWidgetItem) -> Tuple[int, str]:
            group_info = item.data(
                self.COLUMN_GROUP_DS,
                Qt.ItemDataRole.UserRole,
            )

            group_id = (
                group_info.id if isinstance(group_info, GroupInfo) else ""
            )

            if group_id == "OpenStreetMap":
                return (0, "")

            value = item.data(column, role)
            return (1, str(value).lower())

        items = [
            self.root_item.child(index)
            for index in range(self.root_item.childCount())
        ]

        items.sort(key=sort_key, reverse=order != Qt.SortOrder.AscendingOrder)

        self.root_item.takeChildren()

        for item in items:
            self.root_item.addChild(item)

        self.layoutChanged.emit()

    def _check_all(self) -> None:
        """
        Set checked state for all data sources.

        :return: None
        """
        for row in range(0, self.root_item.childCount()):
            group_item = self.root_item.child(row)
            group_index = self.createIndex(
                row, self.COLUMN_VISIBILITY, group_item
            )
            self.setData(
                group_index,
                Qt.CheckState.Checked,
                Qt.ItemDataRole.CheckStateRole,
            )

    def _uncheck_all(self) -> None:
        """
        Set unchecked state for all data sources.

        :return: None
        """
        for row in range(0, self.root_item.childCount()):
            group_item = self.root_item.child(row)
            group_index = self.createIndex(
                row, self.COLUMN_VISIBILITY, group_item
            )
            self.setData(
                group_index,
                Qt.CheckState.Unchecked,
                Qt.ItemDataRole.CheckStateRole,
            )

    def _save_settings(self) -> None:
        """
        Save the current visibility states of data sources into plugin settings.

        :return: None
        """
        settings = QmsSettings()

        hidden_datasource_id_list = []
        for group_index in range(0, self.root_item.childCount()):
            group_item = self.root_item.child(group_index)
            for data_source_index in range(0, group_item.childCount()):
                ds_item = group_item.child(data_source_index)
                if (
                    ds_item.checkState(self.COLUMN_VISIBILITY)
                    == Qt.CheckState.Unchecked
                ):
                    hidden_datasource_id_list.append(
                        ds_item.data(
                            self.COLUMN_GROUP_DS, Qt.ItemDataRole.UserRole
                        ).id
                    )
        settings.hidden_datasource_id_list = hidden_datasource_id_list

    def _is_group(self, index: QModelIndex) -> bool:
        """
        Check whether the index corresponds to a group item.

        :param index: Model index.

        :return: True if item is a group, False otherwise.
        """
        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item == self.root_item:
            return True

        return False

    def _build_tree(
        self,
        groups: Dict[str, List[DataSourceInfo]],
        group_info_map: Dict[str, GroupInfo],
    ) -> None:
        """
        Build tree structure from grouped data sources.

        :param groups: Mapping of group_id to data sources.
        :param group_info_map: Mapping of group metadata.

        :return: None
        """
        for group_id, data_sources in groups.items():
            group_item = self._create_group_item(
                group_id,
                group_info_map,
            )

            self.root_item.addChild(group_item)

            self._add_group_children(
                group_item,
                data_sources,
            )

    def _create_group_item(
        self,
        group_id: str,
        group_info_map: Dict[str, GroupInfo],
    ) -> QTreeWidgetItem:
        """
        Create tree item for a group.

        :param group_id: Group identifier.
        :param group_info_map: Mapping of group metadata.

        :return: Configured group item.
        """
        group_item = QTreeWidgetItem()

        group_info = group_info_map.get(group_id)
        alias = group_info.alias if group_info else group_id

        group_item.setData(
            self.COLUMN_GROUP_DS,
            Qt.ItemDataRole.DisplayRole,
            alias,
        )

        group_item.setCheckState(
            self.COLUMN_VISIBILITY,
            Qt.CheckState.Unchecked,
        )

        group_item.setData(
            self.COLUMN_SOURCE,
            Qt.ItemDataRole.DisplayRole,
            group_info.category if group_info else "",
        )

        if group_info:
            group_item.setIcon(
                self.COLUMN_GROUP_DS,
                QIcon(group_info.icon),
            )
        else:
            group_item.setData(
                self.COLUMN_GROUP_DS,
                Qt.ItemDataRole.DisplayRole,
                "{} ({})".format(
                    group_id,
                    self.tr("group not found"),
                ),
            )

        group_item.setData(
            self.COLUMN_GROUP_DS,
            Qt.ItemDataRole.UserRole,
            group_info,
        )

        return group_item

    def _add_group_children(
        self,
        group_item: QTreeWidgetItem,
        data_sources: List[DataSourceInfo],
    ) -> None:
        """
        Add data source items to a group.

        :param group_item: Parent group item.
        :param data_sources: List of data sources.

        :return: None
        """
        settings = QmsSettings()

        hidden_data_sources_ids = settings.hidden_datasource_id_list

        for data_source in data_sources:
            data_source_item = QTreeWidgetItem()

            data_source_item.setData(
                self.COLUMN_GROUP_DS,
                Qt.ItemDataRole.DisplayRole,
                data_source.alias,
            )
            data_source_item.setIcon(
                self.COLUMN_GROUP_DS,
                QIcon(data_source.icon_path),
            )
            data_source_item.setData(
                self.COLUMN_GROUP_DS,
                Qt.ItemDataRole.UserRole,
                data_source,
            )

            data_source_item.setData(
                self.COLUMN_SOURCE,
                Qt.ItemDataRole.DisplayRole,
                data_source.category if data_source else "",
            )

            check_state = (
                Qt.CheckState.Unchecked
                if data_source.id in hidden_data_sources_ids
                else Qt.CheckState.Checked
            )

            data_source_item.setCheckState(
                self.COLUMN_VISIBILITY,
                check_state,
            )

            if group_item.childCount() == 0:
                group_item.setCheckState(
                    self.COLUMN_VISIBILITY,
                    check_state,
                )
            elif group_item.checkState(self.COLUMN_VISIBILITY) != check_state:
                group_item.setCheckState(
                    self.COLUMN_VISIBILITY,
                    Qt.CheckState.PartiallyChecked,
                )

            group_item.addChild(data_source_item)
