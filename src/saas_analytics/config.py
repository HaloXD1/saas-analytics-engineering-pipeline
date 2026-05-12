from pathlib import Path
from typing import Any

import yaml

from saas_analytics.paths import CONFIG_PATH, PROJECT_ROOT


def project_path(path: str | Path) -> Path:
    return PROJECT_ROOT / path


def load_settings() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
