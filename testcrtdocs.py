import os
import subprocess
import sys

def create_file(path, content):
    """Вспомогательная функция для создания файлов."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Создан файл: {path}")

def main():
    # 1. Определяем пути
    docs_dir = os.path.expanduser("~/Documents/testdocs")
    
    print("="*50)
    print("Генератор документации mini-Zemax")
    print("="*50)
    
    project_root_input = input("Введите путь к репозиторию optical-sim (по умолчанию ~/optical-sim): ").strip()
    project_root = os.path.expanduser(project_root_input) if project_root_input else os.path.expanduser("~/optical-sim")
    
    if not os.path.exists(project_root):
        print(f"Ошибка: Путь '{project_root}' не существует. Проверьте путь и запустите скрипт снова.")
        sys.exit(1)

    # 2. Создаем структуру папок
    print(f"\nСоздание структуры документации в {docs_dir}...")
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(os.path.join(docs_dir, "_static"), exist_ok=True)
    os.makedirs(os.path.join(docs_dir, "_templates"), exist_ok=True)
    os.makedirs(os.path.join(docs_dir, "_build", "html"), exist_ok=True)

    # 3. Генерируем conf.py
    conf_py_content = f"""# docs/conf.py
import os
import sys
sys.path.insert(0, r'{project_root}') # Путь к корню проекта (minizemax)

project = 'mini-Zemax'
copyright = '2026, petros060507'
author = 'petros060507'

extensions = [
    'sphinx.ext.autodoc',      # Автодокументирование из кода
    'sphinx.ext.mathjax',      # LaTeX формулы
    'sphinx.ext.napoleon',     # Поддержка Google/NumPy стиля docstrings
    'sphinxcontrib.mermaid',   # Диаграммы Mermaid
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Настройки autodoc
autodoc_default_options = {{
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'show-inheritance': True,
}}
autodoc_member_order = 'bysource'

# Настройки Mermaid
mermaid_version = "10.6.1"
"""
    create_file(os.path.join(docs_dir, "conf.py"), conf_py_content)

    # 4. Генерируем index.rst
    index_rst_content = """mini-Zemax documentation
========================

Добро пожаловать в документацию по симулятору оптических систем mini-Zemax.
Здесь вы найдете описание архитектуры, математического аппарата и связей между классами.

.. toctree::
   :maxdepth: 2
   :caption: Содержание:

   math_model
   architecture
   api_reference
"""
    create_file(os.path.join(docs_dir, "index.rst"), index_rst_content)

    # 5. Генерируем math_model.rst
    math_rst_content = """Математическая модель
=====================

В этом разделе описан математический аппарат, лежащий в основе симулятора.

Векторный закон Снеллиуса
--------------------------

Реализован в функции :func:`~minizemax.core.physics.snell_vector`.

Основное уравнение для расчета преломленного луча:

.. math::
   :label: snell_vector

   \\eta \\vec{d} + (\\eta \\cos\\theta_i - \\cos\\theta_t) \\vec{n}

Где:
* :math:`\\eta = n_1 / n_2` — отношение показателей преломления.
* :math:`\\theta_i` — угол падения.
* :math:`\\theta_t` — угол преломления.
* :math:`\\vec{n}` — нормаль к поверхности.

Векторное отражение
-------------------

Реализовано в функции :func:`~minizemax.core.physics.reflect_vector`.

.. math::
   :label: reflect_vector

   \\vec{d}_{ref} = \\vec{d} - 2 (\\vec{d} \\cdot \\vec{n}) \\vec{n}

Формулы Френеля
---------------

Реализованы в функции :func:`~minizemax.core.physics.fresnel`.

.. math::
   :label: fresnel_rs

   R_s = \\left| \\frac{n_1 \\cos\\theta_i - n_2 \\cos\\theta_t}{n_1 \\cos\\theta_i + n_2 \\cos\\theta_t} \\right|^2

.. math::
   :label: fresnel_rp

   R_p = \\left| \\frac{n_1 \\cos\\theta_t - n_2 \\cos\\theta_i}{n_1 \\cos\\theta_t + n_2 \\cos\\theta_i} \\right|^2

Параксиальная трассировка
--------------------------

Реализована в модуле :mod:`~minizemax.system.paraxial`.

Основные параксиальные параметры (EFL, BFL, f/#) рассчитываются через трассировку двух параксиальных лучей. Уравнение переноса луча:

.. math::
   :label: paraxial_transfer

   u_{i+1} = \\frac{n_i u_i - y_i (n_{i+1} - n_i) c_i}{n_{i+1}}

Где:
* :math:`y` — высота луча.
* :math:`u` — угол.
* :math:`c = 1/R` — кривизна поверхности.

Суммы Зейделя
-------------

Реализованы в модуле :mod:`~minizemax.analysis.seidel`.

Суммы :math:`S_I - S_V` вычисляются по параксиальному ходу лучей и описывают аберрации третьего порядка. Подробнее см. :func:`~minizemax.analysis.seidel.seidel_sums`.
"""
    create_file(os.path.join(docs_dir, "math_model.rst"), math_rst_content)

    # 6. Генерируем architecture.rst
    arch_rst_content = """Архитектура и связи классов
============================

Пайплайн трассировки лучей
--------------------------

Диаграмма показывает путь луча от источника до детектора:

.. mermaid::

   graph TD
       A[engine.source] -->|Генерация RayBundle| B(engine.tracer.SequentialTracer)
       B -->|Пересечение| C(core.surfaces.OpticalSurface)
       C -->|Преломление/Отражение| D(core.physics)
       B -->|Результат| E(engine.tracer.TraceResult)
       E -->|Анализ| F(analysis.*)

Связи основных классов
-----------------------

*   :class:`~minizemax.engine.tracer.SequentialTracer` — центральный класс, который управляет последовательной трассировкой лучей через список поверхностей.
*   :class:`~minizemax.core.surfaces.OpticalSurface` (и его наследники :class:`~minizemax.core.surfaces.PlaneSurface`, :class:`~minizemax.core.surfaces.SphericalSurface`) — описывают геометрию и оптические свойства каждой поверхности.
*   :class:`~minizemax.core.bundle.RayBundle` — векторизованный контейнер (SoA) для набора лучей, что обеспечивает высокую производительность.
*   :class:`~minizemax.system.paraxial.ParaxialData` — хранит результаты параксиального расчета, которые затем используются для анализа Зейделя (:mod:`~minizemax.analysis.seidel`).

Логика работы и перекрестные ссылки
-----------------------------------

Вы можете ссылаться на конкретные методы прямо в тексте. Например, метод :meth:`~minizemax.engine.tracer.SequentialTracer.trace` является точкой входа для трассировки.

Класс :class:`~minizemax.optim.merit.MeritFunction` использует :func:`~minizemax.engine.tracer.trace_field` для расчета функции оценки и последующей оптимизации.
"""
    create_file(os.path.join(docs_dir, "architecture.rst"), arch_rst_content)

    # 7. Генерируем api_reference.rst
    api_rst_content = """Справочник API
==============

Ядро (core)
-----------

.. automodule:: minizemax.core.physics
   :members:

.. automodule:: minizemax.core.ray
   :members:

.. automodule:: minizemax.core.surfaces
   :members:

.. automodule:: minizemax.core.bundle
   :members:

Движок (engine)
---------------

.. automodule:: minizemax.engine.tracer
   :members:

Система (system)
----------------

.. automodule:: minizemax.system.paraxial
   :members:

Анализ (analysis)
-----------------

.. automodule:: minizemax.analysis.seidel
   :members:

Оптимизация (optim)
-------------------

.. automodule:: minizemax.optim.merit
   :members:
"""
    create_file(os.path.join(docs_dir, "api_reference.rst"), api_rst_content)

    # 8. Установка зависимостей и сборка
    print("\n" + "="*50)
    print("Установка зависимостей и сборка документации...")
    print("="*50)
    
    try:
        # Устанавливаем пакеты
        subprocess.run([sys.executable, "-m", "pip", "install", "sphinx", "sphinx-rtd-theme", "sphinxcontrib-mermaid"], check=True)
        
        # Запускаем сборку Sphinx
        print("\nЗапуск sphinx-build...")
        subprocess.run(["sphinx-build", "-b", "html", docs_dir, os.path.join(docs_dir, "_build", "html")], check=True)
        
        print("\n" + "="*50)
        print("✅ УСПЕХ! Документация успешно собрана.")
        print(f"Откройте файл в браузере: {os.path.join(docs_dir, '_build', 'html', 'index.html')}")
        print("="*50)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при выполнении команды: {e}")
        print("Убедитесь, что у вас установлен Python и pip, и что путь к проекту указан верно.")
    except FileNotFoundError:
        print("\n❌ Ошибка: Команда 'sphinx-build' не найдена. Возможно, Sphinx не установился корректно.")
        print("Попробуйте установить его вручную: pip install sphinx sphinx-rtd-theme sphinxcontrib-mermaid")

if __name__ == "__main__":
    main()