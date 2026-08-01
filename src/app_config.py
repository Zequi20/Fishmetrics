import configparser
from pathlib import Path


class AppConfig:
    """Configuración persistente de FishMetrics respaldada por un archivo INI."""

    DEFAULTS = {
        "appearance": {
            "theme": "light",
        },
    }

    def __init__(self, path=None):
        project_root = Path(__file__).resolve().parent.parent
        self.path = Path(path) if path else project_root / "config.ini"
        self.load_error = None
        self.write_error = None
        self.parser = self._new_parser()
        self._load()

        if not self.path.exists():
            try:
                self.save()
            except OSError as error:
                self.write_error = error

    def _new_parser(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_dict(self.DEFAULTS)
        return parser

    def _load(self):
        if not self.path.exists():
            return

        try:
            with self.path.open("r", encoding="utf-8") as config_file:
                self.parser.read_file(config_file)
        except (OSError, UnicodeError, configparser.Error) as error:
            # Conserva valores seguros para permitir que la aplicación inicie.
            self.parser = self._new_parser()
            self.load_error = error

    def get(self, section, option, fallback=None):
        return self.parser.get(section, option, fallback=fallback)

    def set(self, section, option, value):
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, option, str(value))
        self.save()

    def save(self):
        """Escribe de forma atómica para no dejar un archivo parcial."""
        temp_path = self.path.with_name(f".{self.path.name}.tmp")

        try:
            with temp_path.open("w", encoding="utf-8") as config_file:
                self.parser.write(config_file)
            temp_path.replace(self.path)
            self.write_error = None
        except OSError as error:
            self.write_error = error
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
