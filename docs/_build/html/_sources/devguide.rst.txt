Руководство разработчика
========================

Как добавлять сущности
----------------------

- **Стекло**: запись в ``CATALOG`` (`minizemax/core/materials.py`) — Sellmeier B/C.
- **Поверхность**: наследник ``OpticalSurface`` с ``_intersect_local``; трейсер и
  компоненты подхватят её без правок (acceptance: RayTracer не меняется).
- **Операнд MF**: ветка в ``MeritFunction._value`` + имя в ``KINDS`` (MFE widget).
- **Компонент**: наследник ``OpticalComponent`` (``surfaces()``, ``rows()``, ``length``).
- **Анализ**: функция в ``analysis/``, принимающая ``built``/``TraceResult``.

Карта тестов
------------

.. list-table::
   :header-rows: 1

   * - Тест
     - Что проверяет
   * - ``test_physics.py``
     - Снеллиус скалярно, Брюстер, TIR (:eq:`snell`, :eq:`fresnel`)
   * - ``test_engine.py``
     - TIR убивает лучи, зеркало R/2, синглет: параксиал vs трассировка
   * - ``test_prescription.py``
     - YAML load/build/roundtrip, EFL дублета
   * - ``test_optim.py``
     - DLS уменьшает RMS при ограничении EFFL (:eq:`lm`)
   * - ``test_components.py``
     - Prompt 6: A/B/C + переиспользуемость компонентов
   * - ``test_prompt6.py``
     - acceptance: BLOCKED-статусы, valid+edge на компонент
   * - ``test_scene3d.py`` / ``test_losses.py`` / ``test_names.py``
     - сцена float32/uint32; loss-счётчики; авто-имена LDE

Известные грабли (история багов → решения)
-------------------------------------------

- PyYAML парсит ``inf`` без точки как строку → ``_to_float`` в ``prescription.py``.
- Wayland + ``QOpenGLWidget``: не трогать контекст до show; dirty-build в ``paintGL``.
- dpr: ``glViewport`` по ``width()*devicePixelRatio()``, иначе рендер в углу.
- Мерцание стекла: back-to-front сортировка alpha + ободья ``*0.998`` (z-fighting).
- Typer: параметры со default становятся опциями → ``typer.Argument`` для ``gui``.
