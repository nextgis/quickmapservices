from pathlib import Path

from qgis.core import QgsApplication

from quick_map_services.core.constants import PLUGIN_NAME

DATA_SOURCES_DIR_NAME = "data_sources"
GROUPS_DIR_NAME = "groups"

LOCAL_SETTINGS_PATH = Path(QgsApplication.qgisUserDatabaseFilePath()).parent
PLUGIN_SETTINGS_PATH = LOCAL_SETTINGS_PATH / PLUGIN_NAME

BASE_RESOURCES_PATH = (
    Path(__file__).resolve().parent / "quickmapservices_contrib"
)

USER_DIR_PATH = PLUGIN_SETTINGS_PATH / "User"

# Data sources paths
BASE_DATA_SOURCES_PATH = BASE_RESOURCES_PATH / DATA_SOURCES_DIR_NAME
USER_DATA_SOURCES_PATH = USER_DIR_PATH / DATA_SOURCES_DIR_NAME

ALL_DS_PATHS = [
    BASE_DATA_SOURCES_PATH,
    USER_DATA_SOURCES_PATH,
]

# Groups paths
BASE_GROUPS_PATH = BASE_RESOURCES_PATH / GROUPS_DIR_NAME
USER_GROUPS_PATH = USER_DIR_PATH / GROUPS_DIR_NAME

ALL_GROUP_PATHS = [
    BASE_GROUPS_PATH,
    USER_GROUPS_PATH,
]
