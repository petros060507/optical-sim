#!/usr/bin/env python3
"""fix_docs.py: чинит три категории ошибок сборки Sphinx.
1) ui-модули исключены из autodoc (не ломают сборку).
2) Заголовки .rst подчёркнуты по реальной длине.
3) |текст| в docstring mtf.py экранирован."""
import pathlib
import re

# ── 1. Полная замена ui.rst: без automodule, только описание + mermaid ───────
UI_RST = r"""
Пакет ``minizemax.ui``
======================

PyQt-GUI: LDE, System Data, MFE, вкладки анализа (Layout / Spot / Ray Fan / MTF / 3D),
GPU-виджет и worker для оптимизации. UI-модули не документируются через autodoc
(они состоят из Qt-биндингов); см. архитектуру ниже.

.. note::

    ``ui/qt.py`` — кросс-биндинг PyQt5/6/PySide6; все виджеты импортируют
    только из него, чтобы не зависеть от конкретного бэкенда.

Граф компонентов GUI
--------------------

.. mermaid::

   graph TD
       app[app.main] --> MainWindow
       MainWindow --> LDEWidget
       MainWindow --> SystemWidget
       MainWindow --> MFEWidget
       MainWindow --> PlotTabs
       MainWindow --> OptimizeWorker
       PlotTabs --> GLView3D
       PlotTabs --> matplotlib
       GLView3D --> scene3d[analysis.scene3d]
       LDEWidget --> modelChanged --> refresh
       SystemWidget --> modelChanged --> refresh
       MFEWidget --> modelChanged --> refresh
       OptimizeWorker --> dls[optim.dls]

Сигналы
-------

``modelChanged`` у LDE/System/MFE → ``MainWindow.refresh`` →
пересчёт всех вкладок ``PlotTabs`` (Layout/Spot/RayFan/MTF/3D).
Оптимизация выполняется в ``OptimizeWorker`` (QThread), сигнал
``progress`` пишет в MFE-лог.

Виджеты
-------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Виджет
     - Назначение
   * - ``LDEWidget``
     - Lens Data Editor: строки SurfaceRow, колонки Surf/Name/Radius/Thickness/Glass/Semi-Dia/Conic/Stop/Var R/Var T. Подсветка проблемных строк из валидатора.
   * - ``SystemWidget``
     - System Data: апертура (EPD/STOP/FNO/NA), λ, поля, семплинг.
   * - ``MFEWidget``
     - Merit Function Editor: операнды (RMS/EFFL/TOTR/DIST), таргет, вес, целевые значения.
   * - ``PlotTabs``
     - Вкладки анализа: Layout/Spot(per-field panels)/RayFan/MTF(geo)/3D(GPU). Тулбар matplotlib: zoom/pan/home/save.
   * - ``GLView3D``
     - Собственный GPU-рендер (QOpenGLWidget + PyOpenGL): back-to-front сортировка alpha, CAD-камера (ЛКМ орбита, СКМ/Shift+ЛКМ панорама, колесо зум, дабл-клик reset), клампы по bbox сцены.
   * - ``OptimizeWorker``
     - QThread для DLS, сигнал ``progress`` для MFE-лога и статус-бара.
"""

# ── 2. Патчи остальных файлов ─────────────────────────────────────────────────

PATCHES = [
    # mtf.py docstring: |текст| -> экранирование
    ("minizemax/analysis/mtf.py",
     "|характеристической функции пятна|",
     r"\характеристической функции пятна"),
]


def _fix_titles(path: pathlib.Path) -> bool:
    """Подгоняет длину '=' под длину заголовка (кириллица = 1 символ)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 1 < len(lines) and lines[i + 1].strip() and re.fullmatch(r"[=\-*~`^]+", lines[i + 1].strip()):
            # строка i — заголовок, i+1 — подчёркивание
            # длина в "символах отображения" (len для кириллицы даёт правильное число глифов)
            need = max(len(line), 3)
            ch = lines[i + 1].strip()[0]
            if len(lines[i + 1]) < need:
                lines[i + 1] = ch * need
                changed = True
            out.append(lines[i])
            out.append(lines[i + 1])
            i += 2
            continue
        out.append(line)
        i += 1
    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def main():
    # 1) ui.rst: без automodule
    p = pathlib.Path("docs/ui.rst")
    p.write_text(UI_RST.lstrip("\n"), encoding="utf-8")
    print(f"rewrite {p}")

    # 2) заголовки во всех .rst
    for rel in ["architecture", "math", "core", "system", "engine",
                "analysis", "optim", "components", "cli", "devguide"]:
        p = pathlib.Path(f"docs/{rel}.rst")
        if not p.exists():
            continue
        if _fix_titles(p):
            print(f"titles   {p}")
        else:
            print(f"already  {p}")

    # 3) docstring mtf.py: экранирование |текст|
    for rel, old, new in PATCHES:
        p = pathlib.Path(rel)
        s = p.read_text(encoding="utf-8")
        if new in s:
            print(f"already  {rel}")
            continue
        if old not in s:
            print(f"NOT FOUND {rel}: {old!r}")
            continue
        p.write_text(s.replace(old, new, 1), encoding="utf-8")
        print(f"patched  {rel}")

    print("\nBuild:")
    print("  sphinx-build -b html docs docs/_build/html")
    print("  xdg-open docs/_build/html/index.html")


if __name__ == "__main__":
    main()