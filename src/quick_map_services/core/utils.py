import shutil

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QLocale

from quick_map_services.core.constants import PACKAGE_NAME
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
