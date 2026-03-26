import shutil
from typing import Dict, Iterable, List, Tuple

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale

from quick_map_services.core.constants import PACKAGE_NAME
from quick_map_services.data_source_info import DataSourceInfo
from quick_map_services.group_info import GroupInfo
from quick_map_services.paths_constants import (
    DATA_SOURCES_DIR_NAME,
    GROUPS_DIR_NAME,
    PLUGIN_SETTINGS_PATH,
    USER_DIR_PATH,
)


def locale() -> str:
    """Return the current locale code as a two-letter lowercase string.

    :returns: Two-letter lowercase locale code (e.g., "en", "fr").
    :rtype: str
    """
    override_locale = QgsSettings().value(
        "locale/overrideFlag", defaultValue=False, type=bool
    )
    if not override_locale:
        locale_full_name = QLocale.system().name()
    else:
        locale_full_name = QgsSettings().value("locale/userLocale", "")
    locale = locale_full_name[0:2].lower()

    return locale if locale.lower() != "c" else "en"


def utm_tags(utm_medium: str, *, utm_campaign: str = "constant") -> str:
    """Generate a UTM tag string with customizable medium and campaign.

    :param utm_medium: UTM medium value.
    :type utm_medium: str
    :param utm_campaign: UTM campaign value.
    :type utm_campaign: str
    :returns: UTM tag string.
    :rtype: str
    """
    return (
        f"utm_source=qgis_plugin&utm_medium={utm_medium}"
        f"&utm_campaign={utm_campaign}&utm_term={PACKAGE_NAME}"
        f"&utm_content={locale()}"
    )


def ensure_user_dirs() -> None:
    """
    Ensure that required user directories exist.

    :return: None
    """
    PLUGIN_SETTINGS_PATH.mkdir(parents=True, exist_ok=True)
    USER_DIR_PATH.mkdir(parents=True, exist_ok=True)

    (USER_DIR_PATH / DATA_SOURCES_DIR_NAME).mkdir(exist_ok=True)
    (USER_DIR_PATH / GROUPS_DIR_NAME).mkdir(exist_ok=True)


def cleanup_obsolete_dirs() -> None:
    """
    Remove obsolete directories from plugin storage.

    :return: None
    """
    contrib_path = PLUGIN_SETTINGS_PATH / "Contribute"

    if not contrib_path.exists():
        return

    shutil.rmtree(contrib_path)


def collect_groups(
    data_sources: Iterable[DataSourceInfo],
) -> Dict[str, List[DataSourceInfo]]:
    """
    Group data sources by group id.

    :param data_sources: Iterable of data sources.

    :return: Mapping of group_id to list of data sources.
    """
    groups: Dict[str, List[DataSourceInfo]] = {}

    for data_source in data_sources:
        groups.setdefault(data_source.group, []).append(data_source)

    return groups


def sort_group_ids(
    group_ids: Iterable[str],
) -> List[str]:
    """
    Sort group identifiers with priority.

    :param group_ids: Iterable of group ids.

    :return: Sorted group ids.
    """

    def sort_key(group_id: str) -> Tuple[int, str]:
        if group_id == "OpenStreetMap":
            return (0, "")
        return (1, group_id.lower())

    return sorted(list(group_ids), key=sort_key)


def sort_data_sources(
    data_sources: Iterable[DataSourceInfo],
) -> List[DataSourceInfo]:
    """
    Sort data sources by id.

    :param data_sources: Iterable of data sources.

    :return: Sorted list of data sources.
    """
    return sorted(
        data_sources,
        key=lambda data_source: str(data_source.id),
    )


def filter_hidden_data_sources(
    groups: Dict[str, List[DataSourceInfo]],
    hidden_data_sources_ids: List[str],
) -> Dict[str, List[DataSourceInfo]]:
    """
    Remove hidden data sources from grouped structure.

    :param groups: Grouped data sources.
    :param hidden_data_sources_ids: List of hidden data source ids.

    :return: Filtered groups.
    """
    result: Dict[str, List[DataSourceInfo]] = {}

    for group_id, data_sources in groups.items():
        visible_sources = [
            data_source
            for data_source in data_sources
            if data_source.id not in hidden_data_sources_ids
        ]

        if visible_sources:
            result[group_id] = visible_sources

    return result
