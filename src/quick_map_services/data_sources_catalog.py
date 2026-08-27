# NextGIS QuickMapServices
# Copyright (C) 2026  NextGIS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass
from typing import Dict, Iterable, List

from quick_map_services.core import utils
from quick_map_services.data_source_info import DataSourceInfo
from quick_map_services.data_sources_list import DataSourcesList
from quick_map_services.group_info import GroupInfo
from quick_map_services.groups_list import GroupsList
from quick_map_services.paths_constants import ALL_DS_PATHS, ALL_GROUP_PATHS


@dataclass
class DataSourceGroup:
    """A group of data sources ready for presentation.

    :param info: Group metadata.
    :param data_sources: Ordered services that belong to the group.
    """

    info: GroupInfo
    data_sources: List[DataSourceInfo]


class DataSourcesCatalog:
    """Load and select local and contributed map services."""

    def __init__(self) -> None:
        """Initialize an empty local services catalog."""
        self._data_sources: Dict[str, DataSourceInfo] = {}
        self._groups: Dict[str, GroupInfo] = {}

    def reload(self) -> None:
        """Reload group and service definitions from the local catalog."""
        groups_list = GroupsList(ALL_GROUP_PATHS)
        data_sources_list = DataSourcesList(
            ALL_DS_PATHS,
            group_info_map=groups_list.groups,
        )
        self._groups = groups_list.groups
        self._data_sources = data_sources_list.data_sources

    def grouped_services(
        self,
        categories: Iterable[str],
        hidden_ids: Iterable[str] = (),
    ) -> List[DataSourceGroup]:
        """Return visible services in sorted groups for the given categories.

        :param categories: Service categories to include.
        :param hidden_ids: Identifiers of services excluded from the result.

        :returns: Ordered visible service groups.
        """
        category_set = set(categories)
        hidden_id_set = set(hidden_ids)
        data_sources = [
            data_source
            for data_source in self._data_sources.values()
            if data_source.category in category_set
        ]
        groups = utils.collect_groups(data_sources)
        visible_groups = utils.filter_hidden_data_sources(
            groups,
            list(hidden_id_set),
        )

        result = []
        for group_id in utils.sort_group_ids(visible_groups):
            group_info = self._groups.get(group_id)
            if group_info is None:
                group_info = GroupInfo(group_id=group_id, alias=group_id)

            result.append(
                DataSourceGroup(
                    info=group_info,
                    data_sources=utils.sort_data_sources(
                        visible_groups[group_id]
                    ),
                )
            )

        return result
