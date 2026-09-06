import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import yaml

from helpers.undistortion import UndistortionHelper
from undistortion import CameraUndistortion


RADIAL_FLATPORT_CALIBRATION = {
    "model": "RADIAL",
    "parameters": [
        3423.331755,
        2037.027345,
        1539.03067,
        0.091474,
        -0.280712,
    ],
    "non_svp_model": "FLATPORT",
    "non_svp_parameters": [
        -0.01205108163,
        -0.06294624951,
        0.9979441573,
        0.200620051,
        0.004,
        1,
        1.52,
        1.333,
    ],
    "width": 4096,
    "height": 3072,
}


class CameraUndistortionTests(unittest.TestCase):
    def test_loads_radial_flatport_calibration(self):
        calibration = RADIAL_FLATPORT_CALIBRATION
        undistorter = CameraUndistortion()

        success = undistorter.load_calibration_from_yaml(
            model=calibration["model"],
            parameters=calibration["parameters"],
            image_size=(calibration["width"], calibration["height"]),
            non_svp_model=calibration["non_svp_model"],
            non_svp_parameters=calibration["non_svp_parameters"],
        )

        self.assertTrue(success)
        np.testing.assert_allclose(
            undistorter.camera_matrix,
            [
                [3423.331755, 0, 2037.027345],
                [0, 3423.331755, 1539.03067],
                [0, 0, 1],
            ],
        )
        np.testing.assert_allclose(
            undistorter.dist_coeffs,
            [0.091474, -0.280712, 0, 0, 0],
        )

        info = undistorter.get_calibration_info()
        self.assertEqual(info["camera_model"], "RADIAL")
        self.assertEqual(info["image_size"], (4096, 3072))
        self.assertEqual(info["non_svp_model"], "FLATPORT")
        self.assertFalse(info["non_svp_correction_applied"])

    def test_scales_intrinsics_for_a_resized_image(self):
        undistorter = CameraUndistortion()
        self.assertTrue(
            undistorter.load_calibration_from_yaml(
                model="RADIAL",
                parameters=[1000, 500, 250, 0.1, -0.05],
                image_size=(1000, 500),
            )
        )

        scaled = undistorter._camera_matrix_for_image_size((500, 250))

        np.testing.assert_allclose(
            scaled,
            [[500, 0, 250], [0, 500, 125], [0, 0, 1]],
        )

    def test_accepts_explicit_non_refractive_model(self):
        undistorter = CameraUndistortion()

        success = undistorter.load_calibration_from_yaml(
            model="SIMPLE_PINHOLE",
            parameters=[1000, 500, 250],
            image_size=(1000, 500),
            non_svp_model="NONE",
            non_svp_parameters=[],
        )

        self.assertTrue(success)
        self.assertIsNone(undistorter.non_svp_model)

    def test_rebuilds_maps_when_alpha_changes(self):
        undistorter = CameraUndistortion()
        self.assertTrue(
            undistorter.load_calibration_from_yaml(
                model="RADIAL",
                parameters=[120, 80, 60, 0.08, -0.02],
                image_size=(160, 120),
            )
        )
        image = np.zeros((120, 160, 3), dtype=np.uint8)

        undistorter.undistort_image(image, alpha=0.0)
        first_optimal_matrix = undistorter.optimal_camera_matrix.copy()
        undistorter.undistort_image(image, alpha=1.0)

        self.assertEqual(undistorter.map_alpha, 1.0)
        self.assertFalse(
            np.allclose(first_optimal_matrix, undistorter.optimal_camera_matrix)
        )

    def test_rejects_invalid_flatport_normal(self):
        undistorter = CameraUndistortion()

        success = undistorter.load_calibration_from_yaml(
            model="RADIAL",
            parameters=[1000, 500, 250, 0.1, -0.05],
            image_size=(1000, 500),
            non_svp_model="FLATPORT",
            non_svp_parameters=[0, 0, 2, 0.2, 0.004, 1, 1.52, 1.333],
        )

        self.assertFalse(success)
        self.assertIsNone(undistorter.camera_matrix)


class UndistortionHelperTests(unittest.TestCase):
    def test_gui_loader_accepts_radial_flatport_yaml(self):
        gui = SimpleNamespace(
            undistorter=CameraUndistortion(),
            set_status=Mock(),
            show_error=Mock(),
        )
        helper = UndistortionHelper(gui)

        with tempfile.TemporaryDirectory() as temp_dir:
            calibration_path = Path(temp_dir) / "underwater_radial.yaml"
            calibration_path.write_text(
                yaml.safe_dump(RADIAL_FLATPORT_CALIBRATION),
                encoding="utf-8",
            )
            with patch(
                "helpers.undistortion.filedialog.askopenfilename",
                return_value=str(calibration_path),
            ):
                with patch(
                    "helpers.undistortion.messagebox.showinfo"
                ) as showinfo:
                    helper.load_calibration()

        self.assertEqual(gui.undistorter.calibration_model, "RADIAL")
        self.assertEqual(gui.undistorter.non_svp_model, "FLATPORT")
        gui.show_error.assert_not_called()
        showinfo.assert_called_once()
        self.assertIn("FLATPORT", showinfo.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
