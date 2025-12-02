import logging
import re
from typing import Union

from qgis.core import Qgis, QgsApplication

from quick_map_services.core.compat import QGIS_3_42_2
from quick_map_services.core.constants import PLUGIN_NAME
from quick_map_services.core.settings import QmsSettings

SUCCESS_LEVEL = logging.INFO + 1
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def map_logging_level_to_qgis(level: int) -> Qgis.MessageLevel:
    """Map Python logging level to QGIS message level.

    :param level: Logging level
    :type level: int
    :return: QGIS message level
    :rtype: Qgis.MessageLevel
    """
    if level >= logging.ERROR:
        return Qgis.MessageLevel.Critical
    if level >= logging.WARNING:
        return Qgis.MessageLevel.Warning
    if level == SUCCESS_LEVEL:
        return Qgis.MessageLevel.Success
    if level >= logging.DEBUG:
        return Qgis.MessageLevel.Info

    return Qgis.MessageLevel.NoLevel


def map_qgis_level_to_logging(level: Qgis.MessageLevel) -> int:
    """Map QGIS message level to Python logging level.

    :param level: QGIS message level
    :type level: Qgis.MessageLevel
    :return: Corresponding Python logging level
    :rtype: int
    """
    if level == Qgis.MessageLevel.Critical:
        return logging.ERROR
    if level == Qgis.MessageLevel.Warning:
        return logging.WARNING
    if level == Qgis.MessageLevel.Success:
        return SUCCESS_LEVEL
    if level == Qgis.MessageLevel.Info:
        return logging.INFO

    return logging.NOTSET


class QgisLogger(logging.Logger):
    """Custom logger for QuickMapServices plugin.

    Provides integration with QGIS message log and adds a 'success' level.

    :param name: Logger name
    :type name: str
    :param level: Logging level
    :type level: int
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        """Initialize QgisLogger instance.

        :param name: Logger name
        :type name: str
        :param level: Logging level
        :type level: int
        """
        super().__init__(name, level)

    def log(
        self,
        level: Union[int, Qgis.MessageLevel],
        msg: str,
        *args,  # noqa: ANN002
        **kwargs,  # noqa: ANN003
    ) -> None:
        """Log 'msg % args' with the integer severity 'level'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=True)
        """
        if isinstance(level, Qgis.MessageLevel):
            level = map_qgis_level_to_logging(level)

        super().log(level, msg, *args, **kwargs)

    def success(self, message: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Log a message with SUCCESS level.

        :param message: Log message
        :type message: str
        """
        if self.isEnabledFor(SUCCESS_LEVEL):
            self._log(SUCCESS_LEVEL, message, args, **kwargs)


class QgisLoggerHandler(logging.Handler):
    """Logging handler that sends messages to QGIS message log.

    Formats and routes log records to QgsApplication.messageLog().
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to QGIS message log.

        :param record: Log record
        :type record: logging.LogRecord
        """
        level = map_logging_level_to_qgis(record.levelno)
        message = self.format(record)
        message_log = QgsApplication.messageLog()
        if record.levelno == logging.DEBUG:
            message = f"[DEBUG]    {message}"
        assert message_log is not None

        message_log.logMessage(self._process_html(message), record.name, level)

    def _process_html(self, message: str) -> str:
        """Process message for HTML compatibility in QGIS log.

        :param message: Log message
        :type message: str
        :return: Processed message
        :rtype: str
        """
        message = message.replace(" ", "\u00a0")

        if Qgis.versionInt() < QGIS_3_42_2:
            return message

        # https://github.com/qgis/QGIS/issues/45834
        for tag in ("i", "b"):
            message = re.sub(
                rf"<{tag}\b[^>]*?>", "", message, flags=re.IGNORECASE
            )
            message = re.sub(rf"</{tag}>", "", message, flags=re.IGNORECASE)

        return message


def load_logger() -> QgisLogger:
    """Create and configure QgisLogger instance.

    Temporarily sets QgisLogger as the logger class, then restores the original.

    :return: Configured QgisLogger instance
    :rtype: QgisLogger
    """
    original_logger_class = logging.getLoggerClass()
    logging.setLoggerClass(QgisLogger)
    try:
        logger = logging.getLogger(PLUGIN_NAME)
    finally:
        logging.setLoggerClass(original_logger_class)

    logger.propagate = False

    handler = QgisLoggerHandler()
    logger.addHandler(handler)

    is_debug_logs_enabled = QmsSettings().is_debug_logs_enabled
    logger.setLevel(logging.DEBUG if is_debug_logs_enabled else logging.INFO)
    if is_debug_logs_enabled:
        logger.warning("Debug messages are enabled")

    return logger  # type: ignore[return-value]


def update_logging_level() -> None:
    """Update logging level based on QuickMapServices settings."""
    is_debug_logs_enabled = QmsSettings().is_debug_logs_enabled
    logger.setLevel(logging.DEBUG if is_debug_logs_enabled else logging.INFO)


def unload_logger() -> None:
    """Remove all handlers and reset logger."""
    logger = logging.getLogger(PLUGIN_NAME)

    handlers = logger.handlers.copy()
    for handler in handlers:
        logger.removeHandler(handler)
        handler.close()

    logger.propagate = True


logger = load_logger()
