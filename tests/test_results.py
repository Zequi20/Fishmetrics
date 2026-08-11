import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

from helpers.results import (
    MEASUREMENT_DISPLAY_UNITS,
    ResultsHelper,
    convert_measurement,
    format_measurement,
)


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class ResultsHelperTests(unittest.TestCase):
    def test_supported_units_and_display_format(self):
        self.assertEqual(MEASUREMENT_DISPLAY_UNITS, ("m", "cm", "mm", "píxeles"))
        self.assertAlmostEqual(convert_measurement(200, 0.05, "m"), 0.1)
        self.assertAlmostEqual(convert_measurement(200, 0.05, "cm"), 10)
        self.assertAlmostEqual(convert_measurement(200, 0.05, "mm"), 100)
        self.assertAlmostEqual(convert_measurement(200, 0.05, "píxeles"), 200)
        self.assertEqual(format_measurement(200, 0.05, "cm"), "10.00 cm")
        self.assertEqual(format_measurement(200, 0.05, "píxeles"), "200.0 px")

    def test_yaml_export_contains_all_units_for_all_measurements(self):
        gui = SimpleNamespace(
            measurements={
                "Longitud Total": 400,
                "Longitud Estándar": 320,
                "Longitud Cefálica": 100,
                "Profundidad Corporal": 120,
            },
            pixel_to_cm_ratio=Value(0.05),
            current_image_path="/data/pez.png",
            undistortion_enabled=Value(False),
            aruco_detection=None,
            pixels_entry=Value("200"),
            cm_entry=Value("10"),
        )
        helper = ResultsHelper(gui)

        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = Path(temp_dir) / "resultados.yaml"
            helper._write_results_to_yaml(yaml_path)
            exported = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["fishmetrics"]

        self.assertEqual(exported["archivo"]["nombre"], "pez.png")
        self.assertEqual(exported["escala"]["metodo"], "manual")
        self.assertEqual(len(exported["mediciones"]), 4)
        for measurement in exported["mediciones"]:
            self.assertEqual(
                set(measurement["valores"]),
                {"m", "cm", "mm", "pixeles"},
            )

        total = exported["mediciones"][0]["valores"]
        self.assertEqual(total, {"m": 0.2, "cm": 20.0, "mm": 200.0, "pixeles": 400.0})


if __name__ == "__main__":
    unittest.main()
