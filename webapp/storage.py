from pathlib import Path

from webapp.config import get_settings


def sanitize_filename(value: str, fallback: str = "Документ") -> str:
    cleaned = (value or "").strip()
    for char in '<>:"/\\|?*':
        cleaned = cleaned.replace(char, "_")
    cleaned = " ".join(cleaned.split()).strip(". ")
    return cleaned[:120] or fallback


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


def storage_relative_path(path: Path | None) -> str:
    if not path:
        return ""

    settings = get_settings()
    candidate = Path(path).resolve()
    storage_root = settings.storage_root.resolve()

    try:
        relative = candidate.relative_to(storage_root)
    except ValueError:
        return ""

    return relative.as_posix()


def _estimate_project_dir(project_id: int, project_name: str = "", object_name: str = "") -> Path:
    settings = get_settings()
    base_name = str(object_name or project_name or f"Объект_{project_id}").strip()
    object_label = sanitize_filename(base_name, f"Объект_{project_id}")
    project_dir = settings.estimates_dir / f"{int(project_id):04d}_{object_label}"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def build_estimate_draft_path(
    project_id: int,
    project_name: str = "",
    object_name: str = "",
) -> tuple[Path, str]:
    base_name = str(object_name or project_name or f"Объект_{project_id}").strip()
    project_dir = _estimate_project_dir(project_id, project_name, object_name)
    drafts_dir = project_dir / "Черновики"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{sanitize_filename(base_name, 'Черновик сметы')}.json"
    absolute_path = drafts_dir / file_name
    return absolute_path, storage_relative_path(absolute_path)


def build_estimate_pdf_path(
    project_id: int,
    project_name: str = "",
    object_name: str = "",
) -> tuple[Path, str]:
    base_name = str(object_name or project_name or f"Объект_{project_id}").strip()
    project_dir = _estimate_project_dir(project_id, project_name, object_name)
    file_name = f"{sanitize_filename(base_name, 'СМЕТА')}.pdf"
    absolute_path = project_dir / file_name
    return absolute_path, storage_relative_path(absolute_path)
