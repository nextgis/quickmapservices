from dataclasses import dataclass
from enum import Enum
from typing import Optional

from qgis.PyQt.QtNetwork import QNetworkReply


@dataclass
class QtNetworkErrorInfo:
    """
    Stores information about a specific Qt network error.

    :param code: The QNetworkReply.NetworkError code.
    :type code: QNetworkReply.NetworkError
    :param constant: The string constant representing the error.
    :type constant: str
    :param description: Human-readable description of the error.
    :type description: str
    """

    code: QNetworkReply.NetworkError
    constant: str
    description: str


class QtNetworkError(Enum):
    """
    Enumeration of Qt network errors with associated information.

    Each member contains a QtNetworkErrorInfo instance describing the error.
    """

    NO_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.NoError,
        "NoError",
        "no error condition",
    )
    CONNECTION_REFUSED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ConnectionRefusedError,
        "ConnectionRefusedError",
        "the remote server refused the connection (the server is not accepting requests)",
    )
    REMOTE_HOST_CLOSED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.RemoteHostClosedError,
        "RemoteHostClosedError",
        "the remote server closed the connection prematurely, before the entire reply was received and processed",
    )
    HOST_NOT_FOUND_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.HostNotFoundError,
        "HostNotFoundError",
        "the remote host name was not found (invalid hostname)",
    )
    TIMEOUT_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.TimeoutError,
        "TimeoutError",
        "the connection to the remote server timed out",
    )
    OPERATION_CANCELED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.OperationCanceledError,
        "OperationCanceledError",
        "the operation was canceled via calls to abort() or close() before it was finished.",
    )
    SSL_HANDSHAKE_FAILED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.SslHandshakeFailedError,
        "SslHandshakeFailedError",
        "the SSL/TLS handshake failed and the encrypted channel could not be established. The sslErrors() signal should have been emitted.",
    )
    TEMPORARY_NETWORK_FAILURE_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.TemporaryNetworkFailureError,
        "TemporaryNetworkFailureError",
        "the connection was broken due to disconnection from the network, however the system has initiated roaming to another access point.",
    )
    NETWORK_SESSION_FAILED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.NetworkSessionFailedError,
        "NetworkSessionFailedError",
        "the connection was broken due to disconnection from the network or failure to start the network.",
    )
    BACKGROUND_REQUEST_NOT_ALLOWED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.BackgroundRequestNotAllowedError,
        "BackgroundRequestNotAllowedError",
        "the background request is not currently allowed due to platform policy.",
    )
    TOO_MANY_REDIRECTS_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.TooManyRedirectsError,
        "TooManyRedirectsError",
        "while following redirects, the maximum limit was reached.",
    )
    INSECURE_REDIRECT_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.InsecureRedirectError,
        "InsecureRedirectError",
        "while following redirects, the network detected a redirect from HTTPS to HTTP.",
    )
    PROXY_CONNECTION_REFUSED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProxyConnectionRefusedError,
        "ProxyConnectionRefusedError",
        "the connection to the proxy server was refused.",
    )
    PROXY_CONNECTION_CLOSED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProxyConnectionClosedError,
        "ProxyConnectionClosedError",
        "the proxy server closed the connection prematurely.",
    )
    PROXY_NOT_FOUND_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProxyNotFoundError,
        "ProxyNotFoundError",
        "the proxy host name was not found.",
    )
    PROXY_TIMEOUT_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProxyTimeoutError,
        "ProxyTimeoutError",
        "the connection to the proxy timed out.",
    )
    PROXY_AUTHENTICATION_REQUIRED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProxyAuthenticationRequiredError,
        "ProxyAuthenticationRequiredError",
        "the proxy requires authentication but the provided credentials were not accepted.",
    )
    CONTENT_ACCESS_DENIED = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ContentAccessDenied,
        "ContentAccessDenied",
        "the access to the remote content was denied (HTTP error 403).",
    )
    CONTENT_OPERATION_NOT_PERMITTED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ContentOperationNotPermittedError,
        "ContentOperationNotPermittedError",
        "the operation requested on the remote content is not permitted.",
    )
    CONTENT_NOT_FOUND_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ContentNotFoundError,
        "ContentNotFoundError",
        "the remote content was not found (HTTP error 404).",
    )
    AUTHENTICATION_REQUIRED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.AuthenticationRequiredError,
        "AuthenticationRequiredError",
        "the server requires authentication but did not accept any credentials.",
    )
    CONTENT_RESEND_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ContentReSendError,
        "ContentReSendError",
        "the request needed to be sent again but failed.",
    )
    CONTENT_CONFLICT_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ContentConflictError,
        "ContentConflictError",
        "the request could not be completed due to a conflict with the resource state.",
    )
    CONTENT_GONE_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ContentGoneError,
        "ContentGoneError",
        "the requested resource is no longer available.",
    )
    INTERNAL_SERVER_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.InternalServerError,
        "InternalServerError",
        "the server encountered an unexpected condition.",
    )
    OPERATION_NOT_IMPLEMENTED_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.OperationNotImplementedError,
        "OperationNotImplementedError",
        "the server does not support the requested functionality.",
    )
    SERVICE_UNAVAILABLE_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ServiceUnavailableError,
        "ServiceUnavailableError",
        "the server is unable to handle the request at this time.",
    )
    PROTOCOL_UNKNOWN_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProtocolUnknownError,
        "ProtocolUnknownError",
        "the protocol is not known.",
    )
    PROTOCOL_INVALID_OPERATION_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProtocolInvalidOperationError,
        "ProtocolInvalidOperationError",
        "the requested operation is invalid for this protocol.",
    )
    UNKNOWN_NETWORK_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.UnknownNetworkError,
        "UnknownNetworkError",
        "an unknown network-related error was detected.",
    )
    UNKNOWN_PROXY_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.UnknownProxyError,
        "UnknownProxyError",
        "an unknown proxy-related error was detected.",
    )
    UNKNOWN_CONTENT_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.UnknownContentError,
        "UnknownContentError",
        "an unknown error related to the remote content was detected.",
    )
    PROTOCOL_FAILURE = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.ProtocolFailure,
        "ProtocolFailure",
        "a breakdown in protocol was detected (parsing error, invalid or unexpected responses, etc.).",
    )
    UNKNOWN_SERVER_ERROR = QtNetworkErrorInfo(
        QNetworkReply.NetworkError.UnknownServerError,
        "UnknownServerError",
        "an unknown error related to the server response was detected.",
    )

    @classmethod
    def from_qt(
        cls, value: QNetworkReply.NetworkError
    ) -> Optional["QtNetworkError"]:
        """
        Get the QtNetworkError enum member corresponding to a QNetworkReply.NetworkError value.

        :param value: The QNetworkReply.NetworkError value.
        :type value: QNetworkReply.NetworkError
        :return: The corresponding QtNetworkError enum member, or None if not found.
        :rtype: Optional[QtNetworkError]
        """
        for error in cls:
            if error.value.code == value:
                return error
        return None
