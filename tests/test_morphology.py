import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from morphology import (
    draw_text_with_outline,
    measure_morphology,
    measure_morphology_with_overlay,
)


class MorphologyVisualizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        temp_path = Path(self.temp_dir.name)

        mask = np.zeros((260, 520, 3), dtype=np.uint8)
        cv2.rectangle(mask, (50, 90), (150, 170), (0, 0, 255), -1)
        cv2.rectangle(mask, (151, 70), (390, 190), (0, 255, 0), -1)
        cv2.rectangle(mask, (391, 100), (470, 160), (255, 0, 0), -1)

        original = np.full_like(mask, (35, 70, 105))
        self.mask_path = temp_path / "mask.png"
        self.original_path = temp_path / "original.png"
        self.annotated_path = temp_path / "annotated.png"
        self.overlay_path = temp_path / "overlay.png"
        cv2.imwrite(str(self.mask_path), mask)
        cv2.imwrite(str(self.original_path), original)

    def test_labels_are_in_centimeters_and_overlay_uses_original_image(self):
        with patch(
            "morphology.draw_text_with_outline",
            wraps=draw_text_with_outline,
        ) as draw_text:
            measurements, annotated, overlay = measure_morphology_with_overlay(
                self.mask_path,
                original_image_path=self.original_path,
                cm_per_pixel=0.05,
                show_visualization=False,
                annotated_output_path=self.annotated_path,
                overlay_output_path=self.overlay_path,
            )

        labels = [
            call.args[1]
            for call in draw_text.call_args_list
            if not call.args[1].startswith("Orientacion")
        ]
        self.assertEqual(len(labels), 8)
        self.assertTrue(all(label.endswith(" cm") for label in labels))
        self.assertFalse(any(" px" in label for label in labels))
        self.assertEqual(len(measurements), 4)
        self.assertIsNotNone(annotated)
        self.assertIsNotNone(overlay)
        self.assertTrue(self.annotated_path.exists())
        self.assertTrue(self.overlay_path.exists())

        # Un píxel alejado de las anotaciones conserva el fondo original.
        self.assertTrue(np.array_equal(overlay[250, 510], np.array([35, 70, 105])))
        self.assertTrue(np.array_equal(annotated[250, 510], np.array([0, 0, 0])))

    def test_legacy_measurement_api_still_returns_two_values(self):
        measurements, annotated = measure_morphology(
            self.mask_path,
            show_visualization=False,
            cm_per_pixel=0.05,
            annotated_output_path=self.annotated_path,
        )

        self.assertEqual(len(measurements), 4)
        self.assertIsNotNone(annotated)


if __name__ == "__main__":
    unittest.main()
