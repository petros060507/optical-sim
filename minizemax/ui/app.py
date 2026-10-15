"""Точка входа GUI: python -m minizemax.ui.app [prescription.yaml]"""
from __future__ import annotations
import sys

DEFAULT_YAML = """
system:
  aperture: {type: EPD, value: 25.0}
  wavelengths_um:
    - {l: 0.5876, w: 1.0, primary: true}
    - {l: 0.4861, w: 1.0}
    - {l: 0.6563, w: 1.0}
  fields_deg: [{y: 0.0, w: 1.0}, {y: 3.0, w: 1.0}]
  sampling: {kind: hexapolar, rings: 3}
lens_data:
  - {surf: OBJ, thickness: .inf}
  - {surf: 1, radius: 122.794, thickness: 12.00, glass: N-SK16, semi_dia: 12.5, variables: [radius]}
  - {surf: 2, radius: -83.550, thickness: 2.85,  glass: N-F2,   semi_dia: 12.5, variables: [radius]}
  - {surf: 3, radius: -773.60, thickness: 46.30,                semi_dia: 12.0, stop: true, variables: [radius]}
  - {surf: IMA}
"""


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    from minizemax.ui.qt import QApplication
    from minizemax.system.prescription import Prescription
    from minizemax.ui.main_window import MainWindow

    path = argv[1] if len(argv) > 1 else None
    pres = None
    if path:
        try:
            pres = Prescription.load(path)
        except Exception as e:  # noqa: BLE001
            print(f"error loading {path}: {e}; using default doublet", file=sys.stderr)
    if pres is None:
        pres = Prescription.from_yaml(DEFAULT_YAML)
    app = QApplication(argv[:1])
    win = MainWindow(pres, path)
    win.show()
    return app.exec() if hasattr(app, "exec") else app.exec_()


if __name__ == "__main__":
    sys.exit(main())
