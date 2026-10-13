"""Шим Qt: PyQt5 -> PyQt6 -> PySide6 + нормализация enum'ов и QAction."""
try:
    from PyQt5.QtWidgets import *   # noqa: F401,F403
    from PyQt5.QtCore import *      # noqa: F401,F403
    from PyQt5.QtGui import *       # noqa: F401,F403
    from PyQt5 import QtWidgets, QtCore, QtGui
    BINDING = "PyQt5"
except ImportError:
    try:
        from PyQt6.QtWidgets import *   # noqa: F401,F403
        from PyQt6.QtCore import *      # noqa: F401,F403
        from PyQt6.QtGui import *       # noqa: F401,F403
        from PyQt6 import QtWidgets, QtCore, QtGui
        BINDING = "PyQt6"
    except ImportError:
        from PySide6.QtWidgets import *   # noqa: F401,F403
        from PySide6.QtCore import *      # noqa: F401,F403
        from PySide6.QtGui import *       # noqa: F401,F403
        from PySide6 import QtWidgets, QtCore, QtGui
        BINDING = "PySide6"

if BINDING == "PyQt5":
    from PyQt5.QtWidgets import QAction
    CHECKED, UNCHECKED = Qt.Checked, Qt.Unchecked
    ITEM_EDITABLE, ITEM_ENABLED = Qt.ItemIsEditable, Qt.ItemIsEnabled
    ITEM_CHECKABLE = Qt.ItemIsUserCheckable
    RESIZE_CONTENTS = QHeaderView.ResizeToContents
    DOCK_LEFT, DOCK_RIGHT = Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea
    DOCK_BOTTOM = Qt.BottomDockWidgetArea
else:
    QAction = QtGui.QAction
    if BINDING == "PyQt6":
        CHECKED, UNCHECKED = Qt.CheckState.Checked, Qt.CheckState.Unchecked
        ITEM_EDITABLE, ITEM_ENABLED = Qt.ItemFlag.ItemIsEditable, Qt.ItemFlag.ItemIsEnabled
        ITEM_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
        RESIZE_CONTENTS = QHeaderView.ResizeMode.ResizeToContents
        DOCK_LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
        DOCK_RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
        DOCK_BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
    else:  # PySide6: unscoped enums работают
        CHECKED, UNCHECKED = Qt.Checked, Qt.Unchecked
        ITEM_EDITABLE, ITEM_ENABLED = Qt.ItemIsEditable, Qt.ItemIsEnabled
        ITEM_CHECKABLE = Qt.ItemIsUserCheckable
        RESIZE_CONTENTS = QHeaderView.ResizeToContents
        DOCK_LEFT, DOCK_RIGHT = Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea
        DOCK_BOTTOM = Qt.BottomDockWidgetArea
