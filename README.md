# mini-Zemax — sequential optical design toy (Zemax-like, Python + PyQt)

    pip install -e ".[dev,ui]"
    pytest -q
    minizemax gui examples/doublet.zmx-lite      # PyQt GUI
    minizemax report examples/doublet.zmx-lite
    minizemax spot   examples/doublet.zmx-lite --field 1
    minizemax optimize examples/doublet.zmx-lite --iters 60
    minizemax layout-cmd examples/doublet.zmx-lite --out layout.png
    python examples/run_doublet.py

Слои: core (физика/геометрия), system (LDE/YAML/параксиал), engine (tracer),
analysis (spot/OPD/MTF/Seidel/layout/report), optim (MFE + DLS), ui (PyQt).
