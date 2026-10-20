"""Qt-шим: PyQt6 основной (MZ_QT=pyqt5/pyside6). Звёздочный слой + ЯВНЫЕ гарантии поимённого
экспорта из всех четырёх модулей (QtWidgets/QtCore/QtGui/QtOpenGLWidgets), потому что в PyQt6
QOpenGLWidget переехал в QtOpenGLWidgets, а QAction/QSurfaceFormat — в QtGui."""
import os as _os
import importlib as _il

_pref = _os.environ.get("MZ_QT", "").strip().lower()


def _order():
    if _pref == "pyqt5":
        return ["PyQt5", "PyQt6", "PySide6"]
    if _pref == "pyside6":
        return ["PySide6", "PyQt6", "PyQt5"]
    return ["PyQt6", "PyQt5", "PySide6"]


BINDING = None
for _b in _order():
    try:
        _w = _il.import_module(f"{_b}.QtWidgets")
        _c = _il.import_module(f"{_b}.QtCore")
        _g = _il.import_module(f"{_b}.QtGui")
        try:
            _o = _il.import_module(f"{_b}.QtOpenGLWidgets")   # PyQt6/PySide6
        except ImportError:
            _o = _g                                            # PyQt5: QOpenGLWidget в QtWidgets
        BINDING = _b
        break
    except ImportError:
        continue
if BINDING is None:
    raise ImportError("No Qt binding found: pip install PyQt6")

_MODS = [_w, _c, _g]
if _o is not _g:
    _MODS.append(_o)

# 1) звёздочный слой со всех модулей
for _m in _MODS:
    for _n in dir(_m):
        if not _n.startswith("_"):
            globals()[_n] = getattr(_m, _n)

# 2) ЯВНЫЕ гарантии: имя -> первый попавшийся из _MODS
_EXPLICIT = [
    "QApplication", "QMainWindow", "QDockWidget", "QToolBar", "QStatusBar", "QMenu",
    "QMenuBar", "QToolButton", "QFileDialog", "QMessageBox", "QLabel", "QTableWidget",
    "QTableWidgetItem", "QTabWidget", "QStackedWidget", "QWidget", "QVBoxLayout",
    "QHBoxLayout", "QFormLayout", "QGridLayout", "QGroupBox", "QScrollArea", "QFrame",
    "QSplitter", "QComboBox", "QListWidget", "QPushButton", "QLineEdit", "QSpinBox",
    "QDoubleSpinBox", "QCheckBox", "QRadioButton", "QPlainTextEdit", "QTextEdit",
    "QInputDialog", "QAbstractItemView", "QHeaderView", "QSizePolicy", "QOpenGLWidget",
    "QCursor",
    "Qt", "QTimer", "QObject", "QSize", "QPoint", "QPointF", "QRect", "QRectF",
    "QCoreApplication", "QEvent", "QVariant", "QModelIndex",
    "QSurfaceFormat", "QAction", "QBrush", "QColor", "QPen", "QIcon", "QPixmap",
    "QImage", "QPainter", "QFont", "QKeySequence", "QShortcut", "QGuiApplication",
]
for _n in _EXPLICIT:
    for _m in _MODS:
        if hasattr(_m, _n):
            globals()[_n] = getattr(_m, _n)
            break

# 3) Signal/Slot
if BINDING == "PySide6":
    Signal, Slot = _c.Signal, _c.Slot
elif BINDING == "PyQt6":
    Signal, Slot = _c.pyqtSignal, _c.pyqtSlot
else:
    Signal, Slot = _c.pyqtSignal, _c.pyqtSlot

# 4) Нормализованные константы (scoped-enum PyQt6 / unscoped PyQt5/PySide6)
if BINDING == "PyQt6":
    CHECKED = Qt.CheckState.Checked
    UNCHECKED = Qt.CheckState.Unchecked
    ITEM_EDITABLE = Qt.ItemFlag.ItemIsEditable
    ITEM_ENABLED = Qt.ItemFlag.ItemIsEnabled
    ITEM_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
    RESIZE_CONTENTS = _w.QHeaderView.ResizeMode.ResizeToContents
    DOCK_LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
    DOCK_RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
    DOCK_BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
    SP_EXPANDING = _w.QSizePolicy.Policy.Expanding
    WA_OPAQUE = Qt.WidgetAttribute.WA_OpaquePaintEvent
    WA_NOSYSBG = Qt.WidgetAttribute.WA_NoSystemBackground
else:
    CHECKED = Qt.Checked
    UNCHECKED = Qt.Unchecked
    ITEM_EDITABLE = Qt.ItemIsEditable
    ITEM_ENABLED = Qt.ItemIsEnabled
    ITEM_CHECKABLE = Qt.ItemIsUserCheckable
    RESIZE_CONTENTS = _w.QHeaderView.ResizeToContents
    DOCK_LEFT = Qt.LeftDockWidgetArea
    DOCK_RIGHT = Qt.RightDockWidgetArea
    DOCK_BOTTOM = Qt.BottomDockWidgetArea
    SP_EXPANDING = _w.QSizePolicy.Expanding
    WA_OPAQUE = Qt.WA_OpaquePaintEvent
    WA_NOSYSBG = Qt.WA_NoSystemBackground
