from quick_map_services.qms_external_api_python.api.api_base import (
    ApiClient,
)


class ApiClientV1(ApiClient):
    VERSION = 1

    def get_geoservices(
        self,
        type_filter=None,
        epsg_filter=None,
        search_str=None,
        intersects_boundary=None,
        cumulative_status=None,
        limit=None,
        offset=None,
    ):
        """
        Geoservices list retrieve
        :param type: Type of geoservice - ['tms' | 'wms' | 'wfs' | 'geojson']
        :param epsg: EPSG code of geoservice CRS - any integer. Example: 4326, 3857
        :param search_str: Search name or description. Examples: 'osm', 'satellite', 'transport'
        :param intersects_boundary: Geom (WKT or EWKT format) for filter by intersects with boundary
        :param cumulative_status: Status of service: ['works' | 'problematic' | 'failed']
        :return: List of geoservices
        """
        sub_url = "geoservices/"
        params = {}
        if type_filter:
            params["type"] = type_filter
        if epsg_filter:
            params["epsg"] = epsg_filter
        if search_str:
            params["search"] = search_str
        if intersects_boundary:
            params["intersects_boundary"] = intersects_boundary
        if cumulative_status:
            params["cumulative_status"] = cumulative_status
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self._get_json(self.full_url(sub_url), params)

    def geoservice_info_url(self, gs_id):
        sub_url = f"geoservices/{gs_id}/"
        return self.endpoint_url + "/" + sub_url

    def geoservice_report_url(self, gs_id):
        return self.geoservice_info_url(gs_id) + "?show-report-problem=1"

    def search_geoservices(self, search_str, intersects_boundary=None):
        """
        Shortcut for search geoservices methods
        :param search_str: Search name or description
        :return: List of geoservices
        """
        return self.get_geoservices(
            search_str=search_str, intersects_boundary=intersects_boundary
        )

    def get_geoservice_info(self, geoservice):
        """
        Retrieve geoservice info
        :param geoservice: geoservice id or geoservice object
        :return: geoservice info object
        """
        if isinstance(geoservice, int) or isinstance(geoservice, str):
            gs_id = geoservice
        elif hasattr(geoservice, "id"):
            gs_id = geoservice.id
        elif hasattr(geoservice, "__iter__") and "id" in geoservice:
            gs_id = geoservice["id"]

        else:
            raise ValueError("Invalid geoservice argument")

        sub_url = f"geoservices/{gs_id}/"
        return self._get_json(self.full_url(sub_url))

    def get_icons(self, search_str=None):
        """
        Retrive icons list
        :param search_str: Search name. Examples: 'osm'
        :return: icons list
        """
        sub_url = "icons"
        params = {}

        if search_str:
            params["search"] = search_str

        return self._get_json(self.full_url(sub_url), params)

    def get_icon_info(self, icon):
        """
        Retrieve icon info
        :param icon: icon id or icon object
        :return: icon info object
        """
        if isinstance(icon, int) or isinstance(icon, str):
            icon_id = icon
        elif hasattr(icon, "id"):
            icon_id = icon.id
        elif hasattr(icon, "__iter__") and "id" in icon:
            icon_id = icon["id"]

        else:
            raise ValueError("Invalid icon argument")

        sub_url = "icons/" + str(icon_id)
        return self._get_json(self.full_url(sub_url))

    def get_icon_content(self, icon, width=32, height=32):
        """
        Retrieve icon content
        :param icon: icon id or icon object
        :return: icon img
        """
        if isinstance(icon, int) or isinstance(icon, str):
            icon_id = icon
        elif hasattr(icon, "id"):
            icon_id = icon.id
        elif hasattr(icon, "__iter__") and "id" in icon:
            icon_id = icon["id"]

        else:
            raise ValueError("Invalid icon argument")

        sub_url = "icons/%s/content" % str(icon_id)

        params = {"width": width, "height": height}

        content = self._get_content(self.full_url(sub_url), params=params)
        return content

    def get_default_icon(self, width=32, height=32):
        """
        Retrieve default icon content
        :return: default icon img
        """
        sub_url = "icons/default"
        params = {"width": width, "height": height}

        content = self._get_content(self.full_url(sub_url), params=params)
        return content
