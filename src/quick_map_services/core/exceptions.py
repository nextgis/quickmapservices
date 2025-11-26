import sys
import uuid
from typing import Any, Callable, List, Optional, Tuple

from qgis.core import QgsApplication


class QmsExceptionInfoMixin:
    """Mixin providing common fields and logic for QuickMapServices errors and warnings."""

    _error_id: str
    _log_message: str
    _user_message: str
    _detail: Optional[str]
    _try_again: Optional[Callable[[], Any]]
    _actions: List[Tuple[str, Callable[[], Any]]]

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the exception info mixin.

        :param log_message: Log message for debugging.
        :type log_message: Optional[str]
        :param user_message: Message to display to the user.
        :type user_message: Optional[str]
        :param detail: Additional details about the error.
        :type detail: Optional[str]
        """
        self._error_id = str(uuid.uuid4())

        default_message = QgsApplication.translate(
            "Exceptions", "An error occurred while running the plugin"
        )

        self._log_message = (
            log_message if log_message else default_message
        ).strip()

        self._user_message = (
            user_message if user_message else default_message
        ).strip()

        Exception.__init__(self, self._log_message)  # type: ignore reportArgumentType

        self.add_note("Message: " + self._user_message)

        self._detail = detail
        if self._detail is not None:
            self._detail = self._detail.strip()
            self.add_note("Details: " + self._detail)

        self._try_again = None

        self._actions = []

    @property
    def error_id(self) -> str:
        """Get the unique error identifier.

        :returns: Unique error ID as a string.
        :rtype: str
        """
        return self._error_id

    @property
    def log_message(self) -> str:
        """Get the log message for debugging.

        :returns: Log message.
        :rtype: str
        """
        return self._log_message

    @property
    def user_message(self) -> str:
        """Get the message intended for the user.

        :returns: User message.
        :rtype: str
        """
        return self._user_message

    @property
    def detail(self) -> Optional[str]:
        """Get additional details about the error.

        :returns: Error details or None.
        :rtype: Optional[str]
        """
        return self._detail

    @property
    def try_again(self) -> Optional[Callable[[], Any]]:
        """Get the callable to retry the failed operation.

        :returns: Callable or None.
        :rtype: Optional[Callable[[], Any]]
        """
        return self._try_again

    @try_again.setter
    def try_again(self, try_again: Optional[Callable[[], Any]]) -> None:
        """Set the callable to retry the failed operation.

        :param try_again: Callable to retry or None.
        :type try_again: Optional[Callable[[], Any]]
        """
        self._try_again = try_again

    @property
    def actions(self) -> List[Tuple[str, Callable[[], Any]]]:
        """Get the list of available actions for this exception.

        :returns: List of (action_name, action_callable) tuples.
        :rtype: List[Tuple[str, Callable[[], Any]]]
        """
        return self._actions

    def add_action(self, name: str, callback: Callable[[], Any]) -> None:
        """Add an action to the exception.

        :param name: Name of the action.
        :type name: str
        :param callback: Callable to execute for the action.
        :type callback: Callable[[], Any]
        """
        self._actions.append((name, callback))

    if sys.version_info < (3, 11):

        def add_note(self, note: str) -> None:
            """Add a note to the exception message (for Python < 3.11).

            :param note: Note string to add.
            :type note: str
            :raises TypeError: If note is not a string.
            """
            if not isinstance(note, str):
                message = "Note must be a string"
                raise TypeError(message)
            message: str = self.args[0]
            self.args = (f"{message}\n{note}",)


class QmsError(QmsExceptionInfoMixin, Exception):
    """Base exception for errors in the QuickMapServices plugin.

    Inherit from this class to define custom error types for the plugin.
    """

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        :param log_message: Log message for debugging.
        :type log_message: Optional[str]
        :param user_message: Message to display to the user.
        :type user_message: Optional[str]
        :param detail: Additional details about the error.
        :type detail: Optional[str]
        """
        QmsExceptionInfoMixin.__init__(
            self,
            log_message,
            user_message=user_message,
            detail=detail,
        )
        Exception.__init__(self, self._log_message)


class QmsWarning(QmsExceptionInfoMixin, UserWarning):
    """Base warning for non-critical issues in the QuickMapServices plugin.

    Inherit from this class to define custom warning types for the plugin.
    """

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the warning.

        :param log_message: Log message for debugging.
        :type log_message: Optional[str]
        :param user_message: Message to display to the user.
        :type user_message: Optional[str]
        :param detail: Additional details about the error.
        :type detail: Optional[str]
        """
        QmsExceptionInfoMixin.__init__(
            self,
            log_message,
            user_message=user_message,
            detail=detail,
        )
        Exception.__init__(self, self._log_message)


class QmsReloadAfterUpdateWarning(QmsWarning):
    """Warning raised when the plugin structure has changed after an update.

    This warning indicates that the plugin was successfully updated, but due to changes
    in its structure, it may fail to load properly until QGIS is restarted.
    """

    def __init__(self) -> None:
        """Initialize the warning."""
        # fmt: off
        super().__init__(
            log_message="Plugin structure changed",
            user_message=QgsApplication.translate(
                "Exceptions",
                "The plugin has been successfully updated. "
                "To continue working, please restart QGIS."
            ),
        )
        # fmt: on


class QmsUiLoadError(QmsError):
    """Exception raised when loading a UI file fails.

    :param log_message: Log message for debugging.
    :type log_message: Optional[str]
    :param user_message: Message to display to the user.
    :type user_message: Optional[str]
    :param detail: Additional details about the error.
    :type detail: Optional[str]
    """

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize QmsUiLoadError.

        :param log_message: Log message for debugging.
        :type log_message: Optional[str]
        :param user_message: Message to display to the user.
        :type user_message: Optional[str]
        :param detail: Additional details about the error.
        :type detail: Optional[str]
        """
        default_message = QgsApplication.translate(
            "Exceptions", "Failed to load the user interface."
        )
        log_message = log_message if log_message else default_message
        user_message = user_message if user_message else default_message
        super().__init__(
            log_message=log_message,
            user_message=user_message,
            detail=detail,
        )
