from __future__ import annotations

import json
from pathlib import Path
from typing import Any


import sys


def get_settings_file() -> Path:
    base_dir = (
        Path(sys.executable).parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    return base_dir / "settings.json"


SETTINGS_FILE = get_settings_file()

DEFAULT_SETTINGS: dict[str, Any] = {
    "last_directory": "",
    "output_folder": "Organized_Files",
    "recursive": False,
    "custom_categories": {},
    "detect_duplicates": True,
}


def load_settings() -> dict[str, Any]:
    settings_file = get_settings_file()
    if not settings_file.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    settings = DEFAULT_SETTINGS.copy()
    settings.update(data)
    settings["custom_categories"] = normalize_custom_categories(
        settings.get("custom_categories", {})
    )
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    settings_file = get_settings_file()
    settings_to_save = DEFAULT_SETTINGS.copy()
    settings_to_save.update(settings)
    settings_to_save["custom_categories"] = normalize_custom_categories(
        settings_to_save.get("custom_categories", {})
    )
    settings_file.write_text(
        json.dumps(settings_to_save, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def normalize_custom_categories(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for category, extensions in value.items():
        clean_category = str(category).strip()
        if not clean_category:
            continue

        clean_extensions: list[str] = []
        if isinstance(extensions, str):
            extensions = extensions.replace(",", " ").split()

        for extension in extensions:
            clean_extension = str(extension).strip().lower()
            if not clean_extension:
                continue
            if not clean_extension.startswith("."):
                clean_extension = f".{clean_extension}"
            if clean_extension not in clean_extensions:
                clean_extensions.append(clean_extension)

        if clean_extensions:
            normalized[clean_category] = clean_extensions

    return normalized
