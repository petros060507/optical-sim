Архитектура и связи модулей
===========================

Карта файлов (что за что отвечает)
----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Файл
     - Назначение
   * - ``minizemax/core/ray.py``
     - DTO одного луча (отладка/слайд Stage 1)
   * - ``minizemax/core/bundle.py``
     - SoA-контейнер ``RayBundle`` + статусы ALIVE/BLOCKED/TIR/MISS
   * - ``minizemax/core/transform.py``
     - Локальная <-> глобальная СК поверхностей
   * - ``minizemax/core/materials.py``
     - ``Material`` Protocol, Sellmeier, каталог стёкол, ``n_at``
   * - ``minizemax/core/physics.py``
     - Векторные Снеллиус/отражение/Френель (:eq:`snell`, :eq:`fresnel`)
   * - ``minizemax/core/surfaces.py``
     - ``OpticalSurface`` ABC, ``PlaneSurface``, ``SphericalSurface`` (+conic, Ньютон)
   * - ``minizemax/system/system_data.py``
     - Апертура, λ, поля, семплирование (mutable для UI)
   * - ``minizemax/system/lens_data.py``
     - LDE-строки ``SurfaceRow``, сборка ``BuiltSystem``, ``auto_comments``
   * - ``minizemax/system/prescription.py``
     - YAML load/save (``_to_float`` против 'inf'-строк PyYAML)
   * - ``minizemax/system/paraxial.py``
     - y-nu трассировка: EFL/BFL/f#, зрачки, маргинальный/chief (:eq:`paraxial`)
   * - ``minizemax/system/validation.py``
     - Геометр. валидатор: краевые толщины, sag-определимость
   * - ``minizemax/engine/source.py``
     - ``pupil_grid``, ``make_bundle`` (старт до 1-й поверхности)
   * - ``minizemax/engine/tracer.py``
     - ``SequentialTracer``, ``Detector``, ``TraceResult`` (stop_point/stop_surf)
   * - ``minizemax/analysis/spot.py``
     - ``image_points``, ``spot_stats`` (:eq:`rms`), ``ray_fan``
   * - ``minizemax/analysis/wavefront.py``
     - OPD относительно опорной сферы (:eq:`opd`)
   * - ``minizemax/analysis/mtf.py``
     - Геометрическая MTF (:eq:`mtf`)
   * - ``minizemax/analysis/distortion.py``
     - Дисторсия chief vs параксиал
   * - ``minizemax/analysis/seidel.py``
     - Суммы Зейделя S_I-S_V (:eq:`seidel`)
   * - ``minizemax/analysis/layout.py`` / ``layout3d.py``
     - 2D- и matplotlib-3D раскладки (цвета по статусам лучей)
   * - ``minizemax/analysis/scene3d.py``
     - GPU-сцена: меши поверхностей/ободьев/стопа + полилинии лучей
   * - ``minizemax/analysis/report.py`` / ``losses.py``
     - System Report; бюджет потерь blocked/tir/miss
   * - ``minizemax/optim/merit.py``
     - ``Operand``, ``MeritFunction`` (RMS/EFFL/TOTR/DIST, переменные из LDE)
   * - ``minizemax/optim/dls.py``
     - Левенберг-Марквардт с callback прогресса (:eq:`lm`)
   * - ``minizemax/components/*``
     - Lens/Mirror/Aperture/Detector/Plate как композиции поверхностей
   * - ``minizemax/ui/*``
     - PyQt-GUI: LDE, System Data, MFE, вкладки анализа, GL-виджет, worker
   * - ``minizemax/cli.py``
     - report/spot/optimize/layout3d/view3d/losses/gui/lenscheck
   * - ``examples/*.py|yaml``
     - Демо: дублет, 4f-релеи (3x/4x), триплет Кука, singlet

Зависимости модулей
-------------------

.. mermaid::

   graph TD
       subgraph core
         phys[physics.py] --> surf[surfaces.py]
         mat[materials.py] --> surf
         trf[transform.py] --> surf
         bun[bundle.py]
         phys --> bun
       end
       surf --> lensdata[lens_data.py]
       mat --> parax[paraxial.py]
       lensdata --> pres[prescription.py]
       lensdata --> built[BuiltSystem]
       parax --> src[source.py]
       bun --> trac[tracer.py]
       surf --> trac
       src --> trac
       trac --> ana[analysis: spot/wavefront/mtf/seidel/layout/scene3d/losses]
       parax --> ana
       ana --> opt[optim: merit.py, dls.py]
       pres --> opt
       pres --> ui[ui: LDE/System/MFE/PlotTabs/GLView3D/Worker]
       ana --> ui
       opt --> ui
       ui --> cli[cli.py]
       ana --> cli

Конвейер трассировки (sequence)
-------------------------------

.. mermaid::

   sequenceDiagram
       participant SRC as source.make_bundle
       participant PAR as paraxial_trace
       participant TR as SequentialTracer
       participant SF as OpticalSurface
       participant DT as Detector
       SRC->>PAR: EP: радиус/позиция зрачка
       PAR-->>SRC: ep_r, ep_z, img_z
       SRC->>TR: RayBundle (status=ALIVE), старт до 1-й поверхности
       loop каждая поверхность
           TR->>SF: intersect(o,d)
           SF-->>TR: Hit(t, point, normal, geo, clip)
           TR->>TR: snell/reflect; status: BLOCKED / TIR / MISS
           TR->>TR: stop_point, stop_surf для погибших
       end
       TR->>DT: register(hits)
       TR-->>SRC: TraceResult(bundle, history, stop_point, stop_surf)

Классы и их связи
-----------------

.. mermaid::

   classDiagram
       class OpticalSurface {
           +intersect(o, d) Hit
           +sag(r)
           +semi_dia
       }
       class PlaneSurface
       class SphericalSurface {
           +radius
           +conic
       }
       OpticalSurface <|-- PlaneSurface
       OpticalSurface <|-- SphericalSurface
       class RayBundle {
           +origin
           +direction
           +status
           +alive
       }
       class SequentialTracer {
           +trace(b) TraceResult
       }
       SequentialTracer --> RayBundle
       SequentialTracer --> OpticalSurface
       class SurfaceRow {
           +radius
           +thickness
           +glass
           +comment
           +variables
       }
       class LensData
       class Prescription {
           +from_yaml()
           +save()
           +build() BuiltSystem
       }
       class BuiltSystem {
           +surfaces
           +detector_z
           +stop_idx
       }
       Prescription --> LensData
       LensData --> SurfaceRow
       Prescription --> BuiltSystem
       BuiltSystem --> OpticalSurface
       class OpticalComponent {
           +surfaces()
           +rows()
           +length
       }
       class SphericalLens {
           +R1
           +R2
           +d
           +D
           +efl_paraxial()
       }
       class SphericalMirror
       class ApertureStop
       class DetectorScreen
       class PlaneParallelPlate {
           +lateral_shift()
       }
       OpticalComponent <|-- SphericalLens
       OpticalComponent <|-- SphericalMirror
       OpticalComponent <|-- ApertureStop
       OpticalComponent <|-- DetectorScreen
       OpticalComponent <|-- PlaneParallelPlate
       OpticalComponent --> SurfaceRow : rows()
       class MeritFunction {
           +residuals(x)
           +vars
       }
       class DLSOptimizer {
           +run(callback)
       }
       DLSOptimizer --> MeritFunction
       MeritFunction --> Prescription
