from abc import ABCMeta

from qgis.PyQt.QtCore import QObject


class QObjectMetaClass(ABCMeta, type(QObject)):
    """Defines a metaclass for QObject-based classes.

    QObjectMetaClass: A metaclass that combines ABCMeta (for abstract base
    classes) and the metaclass of QObject, allowing for the creation of
    abstract Qt objects.
    """
