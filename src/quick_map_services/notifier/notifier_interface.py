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

from abc import abstractmethod

from qgis.core import Qgis
from qgis.PyQt.QtCore import QObject

from quick_map_services.shared.qobject_metaclass import QObjectMetaClass


class NotifierInterface(QObject, metaclass=QObjectMetaClass):
    """Interface for displaying messages to the user.

    This interface defines methods for presenting messages, as well as
    dismissing individual or all messages.
    """

    @abstractmethod
    def display_message(
        self,
        message: str,
        *,
        level: Qgis.MessageLevel = Qgis.MessageLevel.Info,
        duration: int = 0,
        **kwargs,  # noqa: ANN003
    ) -> str:
        """Display a message to the user.

        :param message: The message to display.
        :param level: The message level as Qgis.MessageLevel.
        :param duration: Timeout in seconds; 0 requires manual dismissal.
        :return: An identifier for the displayed message.
        """
        ...

    @abstractmethod
    def display_exception(self, error: Exception) -> str:
        """Display an exception as an error message to the user.

        :param error: The exception to display.
        :return: An identifier for the displayed message.
        """
        ...

    @abstractmethod
    def dismiss_message(self, message_id: str) -> None:
        """Dismiss a specific message by its identifier.

        :param message_id: The identifier of the message to dismiss.
        """
        ...

    @abstractmethod
    def dismiss_all(self) -> None:
        """Dismiss all currently displayed messages."""
        ...
