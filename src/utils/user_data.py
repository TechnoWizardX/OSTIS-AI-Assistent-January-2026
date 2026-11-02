from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QStandardPaths

APP_NAME = "IAMOS"
LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
BUNDLED_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def get_user_data_dir() -> Path:
    application = QCoreApplication.instance()
    if application is None:
        raise RuntimeError(
            "Create the Qt application before accessing IAMOS user data."
        )

    application.setApplicationName(APP_NAME)
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not location:
        raise OSError("Qt could not determine the IAMOS user data directory.")

    data_dir = Path(location)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_user_data_file(filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("User data filename must not include a directory.")
    return get_user_data_dir() / filename


def get_legacy_data_file(filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("Legacy data filename must not include a directory.")
    return LEGACY_DATA_DIR / filename


def get_legacy_bundled_data_file(filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("Bundled data filename must not include a directory.")
    return BUNDLED_DATA_DIR / filename
