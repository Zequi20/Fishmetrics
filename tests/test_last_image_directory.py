import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app_config import AppConfig
from gui import FishMorphologyGUI


class LastImageDirectoryTests(unittest.TestCase):
    def test_directory_is_persisted_and_restored_from_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            config_path = root_path / "config.ini"
            image_directory = root_path / "imagenes"
            image_directory.mkdir()
            image_path = image_directory / "pez.png"

            gui = SimpleNamespace(config=AppConfig(config_path))
            FishMorphologyGUI._remember_image_directory(gui, image_path)

            restored_config = AppConfig(config_path)
            restored_gui = SimpleNamespace(config=restored_config)
            initial_directory = FishMorphologyGUI._get_initial_image_directory(
                restored_gui
            )

            self.assertEqual(initial_directory, str(image_directory.resolve()))
            self.assertEqual(
                restored_config.get("paths", "last_image_directory"),
                str(image_directory.resolve()),
            )

    def test_missing_saved_directory_uses_existing_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(Path(temp_dir) / "config.ini")
            missing_directory = Path(temp_dir) / "ya-no-existe"
            config.set("paths", "last_image_directory", missing_directory)
            gui = SimpleNamespace(config=config)

            initial_directory = FishMorphologyGUI._get_initial_image_directory(gui)

            self.assertNotEqual(initial_directory, str(missing_directory))
            self.assertTrue(Path(initial_directory).is_dir())


if __name__ == "__main__":
    unittest.main()
