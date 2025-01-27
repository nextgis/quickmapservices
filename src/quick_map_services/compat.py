from qgis.PyQt.QtCore import QT_VERSION_STR

qt_major_version = int(QT_VERSION_STR.split(".")[0])

if qt_major_version < 6:
    from qgis.PyQt.QtCore import QIODevice

    OpenModeFlag = QIODevice.OpenModeFlag.WriteOnly
else:
    from qgis.PyQt.QtCore import QIODeviceBase

    OpenModeFlag = QIODeviceBase.OpenModeFlag.WriteOnly
