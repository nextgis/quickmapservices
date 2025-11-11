import json
from typing import Any, Dict, Optional

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QUrl, QUrlQuery
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from quick_map_services.core.settings import QmsSettings
from quick_map_services.qms_external_api_python.api.qt_network_error import (
    QtNetworkError,
)


class QmsNews:
    """
    Represents localized news content for QuickMapServices.
    """

    def __init__(self, i18n_texts: Dict[str, str]) -> None:
        """
        Initialize QmsNews with translations.

        :param i18n_texts: Dictionary mapping language codes to text.
        :type i18n_texts: Dict[str, str]
        """
        self.i18n_texts = i18n_texts

    def get_text(self, lang: str) -> Optional[str]:
        """
        Retrieve news text in the specified language.

        :param lang: Language code (e.g., "en", "ru").
        :type lang: str

        :return: Localized news text or None if not available.
        :rtype: Optional[str]
        """
        return self.i18n_texts.get(lang, self.i18n_texts.get("en"))


class ApiClient:
    """
    Base API client for QuickMapServices.

    This class performs HTTP requests through
    :class:`QgsNetworkAccessManager`, ensuring full integration
    with QGIS network settings and proxy configuration.
    """

    VERSION: int = 0

    def __init__(self, endpoint_url: Optional[str] = None) -> None:
        """
        Initialize the API client.

        :param endpoint_url: Base API endpoint URL.
        :type endpoint_url: Optional[str]
        """
        settings = QmsSettings()
        self.endpoint_url = (
            endpoint_url if endpoint_url is not None else settings.endpoint_url
        )

    @property
    def base_url(self) -> str:
        """
        Construct the base URL including the API version.

        :return: Base API URL.
        :rtype: str
        """
        return f"{self.endpoint_url}/api/v{self.VERSION}/"

    def full_url(self, sub_url: str) -> str:
        """
        Build a full URL from the base endpoint and a subpath.

        :param sub_url: Relative path for the request.
        :type sub_url: str

        :return: Fully qualified API URL.
        :rtype: str
        """
        return f"{self.base_url}{sub_url}"

    def _get_content(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Perform a blocking GET request and return raw binary content.

        :param url: The full URL to request.
        :type url: str
        :param params: Optional dictionary of query parameters.
        :type params: Optional[Dict[str, Any]]

        :return: Raw response content as bytes.
        :rtype: bytes
        """
        qurl_query = QUrlQuery()
        params = {} if params is None else params
        for key, value in params.items():
            qurl_query.addQueryItem(str(key), str(value))
        qurl = QUrl(url)
        qurl.setQuery(qurl_query)

        request = QNetworkRequest(qurl)
        response = QgsNetworkAccessManager.instance().blockingGet(request)

        if response.error() != QNetworkReply.NetworkError.NoError:
            error = QtNetworkError.from_qt(response.error())
            error_code = error.value.code
            message = error.value.description if error is not None else ""
            raise ConnectionError(error_code, message)

        return response.content().data()

    def _get_json(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Perform a GET request and return decoded JSON data.

        :param url: The full URL to request.
        :type url: str
        :param params: Optional query parameters.
        :type params: Optional[Dict[str, Any]]

        :return: Parsed JSON response.
        :rtype: Any
        """
        content = self._get_content(url, params)
        return json.loads(content.decode("utf-8"))

    def get_news(self) -> Optional["QmsNews"]:
        """
        Retrieve localized news information from the static QMS endpoint.

        :return: QmsNews instance or None if unavailable.
        :rtype: Optional[QmsNews]
        """
        url = f"{self.endpoint_url}/static/news.json"
        try:
            content = self._get_content(url)
            news_json = json.loads(content.decode("utf-8"))
            return QmsNews(
                {
                    "en": news_json.get("text_en"),
                    "ru": news_json.get("text_ru"),
                }
            )
        except Exception:
            return None
