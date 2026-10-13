"""Шим Qt: PyQt5 -> PyQt6 -> PySide6 + нормализация имён и enum'ов."""
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

# QAction: в PyQt5 — в QtWidgets, в PyQt6/PySide6 — в QtGui
if BINDING == "PyQt5":
    from PyQt5.QtWidgets import QAction
else:
    QAction = QtGui.QAction

# Signal/Slot: в PyQt5/PyQt6 называются pyqtSignal / pyqtSlot
if BINDING == "PySide6":
    from PySide6.QtCore import Signal, Slot
elif BINDING == "PyQt6":
    from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
else:
    from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

# Check state и item-флаги
if BINDING == "PyQt6":
    CHECKED   = Qt.CheckState.Checked
    UNCHECKED = Qt.CheckState.Unchecked
    ITEM_EDITABLE  = Qt.ItemFlag.ItemIsEditable
    ITEM_ENABLED   = Qt.ItemFlag.ItemIsEnabled
    ITEM_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
    RESIZE_CONTENTS = QHeaderView.ResizeMode.ResizeToContents
    DOCK_LEFT   = Qt.DockWidgetArea.LeftDockWidgetArea
    DOCK_RIGHT  = Qt.DockWidgetArea.RightDockWidgetArea
    DOCK_BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
elif BINDING == "PyQt5":
    CHECKED   = Qt.Checked
    UNCHECKED = Qt.Unchecked
    ITEM_EDITABLE  = Qt.ItemIsEditable
    ITEM_ENABLED   = Qt.ItemIsEnabled
    ITEM_CHECKABLE = Qt.ItemIsUserCheckable
    RESIZE_CONTENTS = QHeaderView.ResizeToContents
    DOCK_LEFT   = Qt.LeftDockWidgetArea
    DOCK_RIGHT  = Qt.RightDockWidgetArea
    DOCK_BOTTOM = Qt.BottomDockWidgetArea
else:
    CHECKED   = Qt.Checked
    UNCHECKED = Qt.Unchecked
    ITEM_EDITABLE  = Qt.ItemIsEditable
    ITEM_ENABLED   = Qt.ItemIsEnabled
    ITEM_CHECKABLE = Qt.ItemIsUserCheckable
    RESIZE_CONTENTS = QHeaderView.ResizeToContents
    DOCK_LEFT   = Qt.LeftDockWidgetArea
    DOCK_RIGHT  = Qt.RightDockWidgetArea
    DOCK_BOTTOM = Qt.BottomDockWidgetArea