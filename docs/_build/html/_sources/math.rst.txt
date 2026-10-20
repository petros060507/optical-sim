Математический аппарат (с привязкой к коду)
===========================================

Преломление и отражение
-----------------------

Векторный закон Снеллиуса с проверкой ПВО:

.. math::
   :label: snell

   \mathbf{d}' = \eta\,\mathbf{d} + (\eta\cos\theta_i - \cos\theta_t)\,\mathbf{n},
   \quad \eta = n_1/n_2,\quad \sin^2\theta_t = \eta^2(1-\cos^2\theta_i) > 1 \Rightarrow \text{TIR}

Код: :py:func:`minizemax.core.physics.snell_vector`, ориентация нормали
:py:func:`minizemax.core.physics.orient_normal`, статус ``STATUS_TIR`` ставится в
:py:meth:`minizemax.engine.tracer.SequentialTracer.trace`.

Френель (интенсивности):

.. math::
   :label: fresnel

   R_s = \left(\frac{n_1\cos\theta_i - n_2\cos\theta_t}{n_1\cos\theta_i + n_2\cos\theta_t}\right)^2,
   \quad
   R_p = \left(\frac{n_1\cos\theta_t - n_2\cos_i}{n_1\cos\theta_t + n_2\cos_i}\right)^2

Код: :py:func:`minizemax.core.physics.fresnel` (угол Брюстера покрыт тестом).

Саг и пересечение сферы
-----------------------

Коническая поверхность:

.. math::
   :label: sag

   z(r) = \frac{r^2}{R\left(1+\sqrt{1-(1+k)r^2/R^2}\right)}

Код: :py:meth:`minizemax.core.surfaces.SphericalSurface.sag`; пересечение — квадратное
уравнение по сфере + 3 итерации Ньютона по :eq:`sag`; условие «шапки»
:math:`(p_z-R)R<0`. Апертурный клип даёт ``STATUS_BLOCKED``
(:py:class:`minizemax.core.surfaces.Hit.clip`).

Параксиал (y-nu)
----------------

.. math::
   :label: paraxial

   n'u' = nu - y\varphi,\quad \varphi=(n'-n)c,\qquad y_{i+1} = y_i + t_i u'_i

Из базисных лучей A(1,0), B(0,1): :math:`f' = -1/u'_A`, chief через стоп,
EP/XP — пересечения с осью. Код: :py:func:`minizemax.system.paraxial.paraxial_trace`,
:py:func:`minizemax.system.paraxial._trace_ray`.

Формула шлифовщика и пластина
------------------------------

.. math::
   :label: lensmaker

   \frac{1}{f} = (n-1)\left[\frac{1}{R_1} - \frac{1}{R_2} + \frac{(n-1)d}{n R_1 R_2}\right]

Код: :py:meth:`minizemax.components.lens.SphericalLens.efl_paraxial`
(плоская сторона :math:`R=\infty` даёт нулевой вклад).

.. math::
   :label: plate

   s = d\sin\theta\left(1 - \frac{\cos\theta}{\sqrt{n^2-\sin^2\theta}}\right)

Код: :py:meth:`minizemax.components.plate.PlaneParallelPlate.lateral_shift`
(test system A: направление сохраняется, сход равен :eq:`plate`).

4f-релей
--------

.. math::
   :label: fourf

   d(H_2^{(1)} \to H_1^{(2)}) = f_1 + f_2,\qquad M = -\frac{f_2}{f_1}

Код/демо: ``examples/fourf_relay.py`` измеряет :math:`M` трассировкой конечного
объекта; афокальность в GUI отображается как ``EFL=inf``.

Зейдель
-------

.. math::
   :label: seidel

   \begin{aligned}
   S_I &= \sum y A^2 \Delta(u/n), & S_{II} &= \sum y A\bar A \Delta(u/n), \\
   S_{III} &= \sum y \bar A^2 \Delta(u/n), & S_{IV} &= \sum H^2 c\, \Delta(1/n), \\
   S_V &= \sum \frac{\bar A^3}{A} y \Delta(u/n) + \frac{\bar A}{A} H^2 c\, \Delta(1/n),
   \end{aligned}

где :math:`A = n(yc + u_b)`, :math:`H = n_1(\bar y u_b - y \bar u_b)`.
Код: :py:func:`minizemax.analysis.seidel.seidel_sums`.

OPD и MTF
---------

.. math::
   :label: opd

   W = \mathrm{OPL} + \left(\lVert P - C\rVert - R\right) - W_{chief},
   \quad C = \text{гауссова точка},\ R = |z_{img} - z_{XP}|

Код: :py:func:`minizemax.analysis.wavefront.opd_waves` (волны: деление на λ).

.. math::
   :label: mtf

   \mathrm{MTF}(\nu) = \left|\frac{\sum w_i e^{-2\pi i \nu r_i}}{\sum w_i}\right|,
   \qquad \nu_c = \frac{1}{\lambda\, (f/\#)}

Код: :py:func:`minizemax.analysis.mtf.mtf_geometric`.

Пятно и оптимизация
-------------------

.. math::
   :label: rms

   \mathrm{RMS} = \sqrt{\frac{\sum w_i d_i^2}{\sum w_i}},\quad d_i = \lVert p_i - \bar c\rVert

Код: :py:func:`minizemax.analysis.spot.spot_stats`; операнд ``RMS`` в
:py:class:`minizemax.optim.merit.MeritFunction`.

.. math::
   :label: lm

   \left(J^\top J + \lambda\,\mathrm{diag}(J^\top J)\right)\delta = -J^\top f,
   \quad x \leftarrow \mathrm{clip}(x+\delta)

Код: :py:meth:`minizemax.optim.dls.DLSOptimizer.run` (J — конечные разности,
λ-подбор до 12 попыток, callback прогресса для GUI/CLI).
