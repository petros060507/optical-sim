"""Unified dark 'modern optics CAD' theme for all mini-Zemax views."""
from __future__ import annotations

BG = "#0b0f14"
PANEL = "#10161d"
GRID = "#1b2530"
AXIS = "#39465a"
TEXT = "#c9d1d9"
ACCENT = "#58a6ff"

GLASS_FILL = (110, 179, 255, 46)
GLASS_EDGE = "#6fb3ff"
MIRROR = "#d7dde5"
STOP = "#ff9f43"
DETECTOR = "#2ee6a8"

RAY = (255, 209, 102, 210)
RAY_BLOCKED = (255, 107, 107, 230)
RAY_TIR = (199, 125, 255, 230)
RAY_MISS = (138, 147, 153, 160)

FIELDS = ["#ffd166", "#6fb3ff", "#2ee6a8", "#c77dff", "#ff9f43"]


def mpl_dark_style():
    """Apply the theme to matplotlib (fallback backend only)."""
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
        "axes.edgecolor": AXIS, "axes.labelcolor": TEXT, "xtick.color": TEXT,
        "ytick.color": TEXT, "text.color": TEXT, "grid.color": GRID,
        "axes.grid": True, "grid.alpha": 0.35, "font.size": 8,
        "axes.titlesize": 9, "legend.framealpha": 0.25, "legend.facecolor": PANEL,
    })


def pg_dark(pg):
    pg.setConfigOptions(background=BG, foreground=TEXT, antialias=True)


def apply_app_palette(app):
    """Best-effort dark QPalette for widgets (no external theme deps)."""
    from minizemax.ui.qt import QColor, QPalette
    pal = QPalette()
    for role in ("Window", "Base", "Button", "WindowText", "ButtonText", "Text",
                 "Highlight", "HighlightedText", "ToolTipBase", "ToolTipText"):
        r = getattr(QPalette, role, None) or getattr(QPalette, "ColorRole", object)()
        try:
            r = getattr(QPalette, role)
        except AttributeError:
            continue
        dark = role in ("Window", "Base", "Button", "ToolTipBase")
        pal.setColor(r, QColor(PANEL if dark else TEXT))
    try:
        app.setPalette(pal)
    except Exception:
        pass
