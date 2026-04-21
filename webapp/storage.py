from pathlib import Path

from webapp.config import get_settings


def ensure_storage_dirs() -> None:
    settings = get_settings()
    for path in (
        settings.storage_root,
        settings.contracts_dir,
        settings.estimates_dir,
        settings.uploads_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def resolve_storage_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None

    settings = get_settings()
    normalized = relative_path.replace("\\", "/").lstrip("/")
    candidate = (settings.storage_root / normalized).resolve()
    storage_root = settings.storage_root.resolve()

    try:
        candidate.relative_to(storage_root)
    except ValueError:
        return None

    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate
