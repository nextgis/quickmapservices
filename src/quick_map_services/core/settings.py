import ast
import platform
from typing import Any, ClassVar, Dict, List, Tuple

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QByteArray, QDir, QSettings, Qt


class QmsSettings:
    """Centralized settings handler for the QuickMapServices (QMS) plugin."""

    COMPANY_NAME = "NextGIS"
    PRODUCT = "QuickMapServices"

    KEY_HIDDEN_DATASOURCE_ID_LIST = (
        f"{COMPANY_NAME}/{PRODUCT}/hiddenDatasourceIdList"
    )
    KEY_DEFAULT_USER_ICON_PATH = (
        f"{COMPANY_NAME}/{PRODUCT}/ui/defaultUserIconPath"
    )
    KEY_LAST_ICON_PATH = f"{COMPANY_NAME}/{PRODUCT}/lastIconPath"
    KEY_ENABLE_OTF_3857 = f"{COMPANY_NAME}/{PRODUCT}/enableOtf3857"
    KEY_SHOW_MESSAGES_IN_BAR = f"{COMPANY_NAME}/{PRODUCT}/showMessagesInBar"
    KEY_LAST_USED_SERVICES = f"{COMPANY_NAME}/{PRODUCT}/lastUsedServices"
    KEY_ENDPOINT_URL = f"{COMPANY_NAME}/{PRODUCT}/endpointUrl"

    __is_updated: ClassVar[bool] = False
    __settings: QgsSettings

    def __init__(self) -> None:
        self.__settings = QgsSettings()
        self.__update_settings()

    @property
    def show_messages_in_bar(self) -> bool:
        return self.__settings.value(
            self.KEY_SHOW_MESSAGES_IN_BAR,
            defaultValue=True,
            type=bool,
        )

    @show_messages_in_bar.setter
    def show_messages_in_bar(self, value: bool) -> None:
        self.__settings.setValue(self.KEY_SHOW_MESSAGES_IN_BAR, value)

    @property
    def enable_otf_3857(self) -> bool:
        return self.__settings.value(
            self.KEY_ENABLE_OTF_3857,
            defaultValue=False,
            type=bool,
        )

    @enable_otf_3857.setter
    def enable_otf_3857(self, value: bool) -> None:
        self.__settings.setValue(self.KEY_ENABLE_OTF_3857, value)

    @property
    def last_icon_path(self) -> str:
        return self.__settings.value(
            self.KEY_LAST_ICON_PATH,
            defaultValue=QDir.homePath(),
            type=str,
        )

    @last_icon_path.setter
    def last_icon_path(self, value: str) -> None:
        self.__settings.setValue(self.KEY_LAST_ICON_PATH, value)

    @property
    def hidden_datasource_id_list(self) -> List[str]:
        """List of hidden datasource IDs."""
        result = self.__settings.value(
            self.KEY_HIDDEN_DATASOURCE_ID_LIST,
            defaultValue="",
            type=str,
        )
        return [source for source in result.split(";") if source]

    @hidden_datasource_id_list.setter
    def hidden_datasource_id_list(self, values: List[str]) -> None:
        self.__settings.setValue(
            self.KEY_HIDDEN_DATASOURCE_ID_LIST,
            ";".join(values),
        )

    @property
    def last_used_services(self) -> List[Tuple[Dict[str, Any], QByteArray]]:
        """Retrieve the last used services stored in settings."""
        result = []
        settings = self.__settings
        base_path = self.KEY_LAST_USED_SERVICES

        settings.beginGroup(base_path)
        for service_id in settings.childGroups():
            service_json_str = settings.value(f"{service_id}/json", None)
            if not service_json_str:
                continue
            service_json = ast.literal_eval(service_json_str)
            image_ba = settings.value(f"{service_id}/image", type=QByteArray)
            result.append((service_json, image_ba))
        settings.endGroup()

        return result

    @last_used_services.setter
    def last_used_services(self, services) -> None:
        """Save the given geoservices to the settings."""
        settings = self.__settings
        base_path = self.KEY_LAST_USED_SERVICES
        settings.remove(base_path)
        settings.beginGroup(base_path)
        for geoservice in services:
            geoservice.save_self(settings)
        settings.endGroup()

    @property
    def default_user_icon_path(self) -> str:
        """
        Get the default path for user-defined icons.

        :return: Path to the last selected user icon.
        :rtype: str
        """
        result = self.__settings.value(self.KEY_DEFAULT_USER_ICON_PATH, "")
        if isinstance(result, tuple):
            return result[0]
        return result

    @default_user_icon_path.setter
    def default_user_icon_path(self, value: str) -> None:
        """
        Set the default path for user-defined icons.

        :param value: Path to the user icon.
        :type value: str
        :return: None
        :rtype: None
        """
        self.__settings.setValue(self.KEY_DEFAULT_USER_ICON_PATH, value)

    @property
    def default_endpoint_url(self) -> str:
        return "https://qms.nextgis.com"

    @property
    def endpoint_url(self) -> str:
        return self.__settings.value(
            self.KEY_ENDPOINT_URL,
            defaultValue=self.default_endpoint_url,
            type=str,
        )

    @endpoint_url.setter
    def endpoint_url(self, value: str) -> None:
        normalized_endpoint = value.strip().rstrip("/")
        self.__settings.setValue(self.KEY_ENDPOINT_URL, normalized_endpoint)

    @classmethod
    def __update_settings(cls) -> None:
        """Perform one-time migration from old QSettings storage."""
        if cls.__is_updated:
            return
        qgs_settings = QgsSettings()
        cls.__migrate_from_qsettings(qgs_settings)
        cls.__is_updated = True

    @classmethod
    def __migrate_from_qsettings(cls, qgs_settings: QgsSettings) -> None:
        """Migrate from QSettings to QgsSettings"""
        old_settings = QSettings(cls.COMPANY_NAME, cls.PRODUCT)
        if platform.system() != "Darwin" and len(old_settings.allKeys()) == 0:
            return

        settings_key_map = {
            "hide_ds_id_list_str": cls.KEY_HIDDEN_DATASOURCE_ID_LIST,
            "ui/default_user_icon_path": cls.KEY_DEFAULT_USER_ICON_PATH,
            "last_icon_path": cls.KEY_LAST_ICON_PATH,
            "enable_otf_3857": cls.KEY_ENABLE_OTF_3857,
            "show_messages_in_bar": cls.KEY_SHOW_MESSAGES_IN_BAR,
        }

        for old_key, new_key in settings_key_map.items():
            value = old_settings.value(old_key)
            if value is not None:
                qgs_settings.setValue(new_key, value)
                old_settings.remove(old_key)

        cls.__migrate_last_used_services(old_settings, qgs_settings)

        # remove deprecated settings
        old_settings.remove("ui/dockWidgetArea")
        old_settings.remove("ui/dockWidgetIsVisible")
        old_settings.remove("tile_layer/default_connection_count")
        old_settings.remove("tile_layer/use_native_tms")

    @classmethod
    def __migrate_last_used_services(
        cls, old_settings: QSettings, qgs_settings: QgsSettings
    ) -> None:
        """Migrate nested lastUsedServices group structure."""
        old_settings.beginGroup("last_used_services")
        service_ids = old_settings.childGroups()
        if not service_ids:
            old_settings.endGroup()
            return

        qgs_settings.beginGroup(cls.KEY_LAST_USED_SERVICES)

        for service_id in service_ids:
            old_settings.beginGroup(service_id)
            json_value = old_settings.value("json", None)
            raw_image_value = old_settings.value("image", None)
            image_value = (
                QByteArray(raw_image_value)
                if raw_image_value is not None
                else None
            )

            if json_value is not None:
                qgs_settings.setValue(f"{service_id}/json", json_value)
            if image_value is not None:
                qgs_settings.setValue(f"{service_id}/image", image_value)

            old_settings.endGroup()

        qgs_settings.endGroup()
        old_settings.endGroup()
        old_settings.remove("last_used_services")
