CLI, примеры и скрипты
======================

.. automodule:: minizemax.cli
   :members:

Команды
-------

.. list-table::
   :header-rows: 1

   * - Команда
     - Действие
   * - ``minizemax report <yaml>``
     - System Report + Loss budget
   * - ``minizemax spot <yaml> --field N``
     - RMS/GEO пятна поля N
   * - ``minizemax optimize <yaml> --iters K --save out.yaml``
     - DLS по Default MF (:eq:`lm`)
   * - ``minizemax layout3d <yaml> [--show]``
     - matplotlib-3D раскладка
   * - ``minizemax view3d <yaml>``
     - GPU-окно (QOpenGLWidget)
   * - ``minizemax losses <yaml>``
     - бюджет blocked/tir/miss
   * - ``minizemax lenscheck <yaml>``
     - формы линз: саги, толщины центра/края
   * - ``minizemax gui [yaml]``
     - PyQt-GUI (LDE/System/MFE/Analysis/3D)

Примеры-скрипты
---------------

- ``examples/run_doublet.py`` — report -> spot/OPD до -> DLS -> после -> PNG.
- ``examples/fourf_relay.py`` — увеличение конечного объекта трассировкой (:eq:`fourf`).
- ``examples/view3d.py`` — интерактивный matplotlib-3D без GUI.
- ``examples/components_demo.py`` — test systems A/B/C из компонентов.
