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
