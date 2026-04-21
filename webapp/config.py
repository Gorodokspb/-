import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = BASE_DIR / ".env.web"


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    postgres_dsn: str
    secret_key: str
    admin_username: str
    admin_password: str
    storage_root: Path
    contracts_dir: Path
    estimates_dir: Path
    uploads_dir: Path
    web_host: str
    web_port: int


def get_settings() -> Settings:
    env_file = Path(os.environ.get("DEKORCRM_WEB_ENV_FILE", str(DEFAULT_ENV_FILE)))
    load_env_file(env_file)

    postgres_dsn = (
        os.environ.get("DEKORCRM_POSTGRES_DSN")
        or os.environ.get("POSTGRES_DSN")
        or ""
    ).strip()
    if not postgres_dsn:
        raise RuntimeError(
            "Не задан PostgreSQL DSN. Укажите DEKORCRM_POSTGRES_DSN или POSTGRES_DSN."
        )

    storage_root = Path(
        os.environ.get("DEKORCRM_STORAGE_ROOT", str(BASE_DIR / "server_storage"))
    )
    contracts_dir = Path(
        os.environ.get("DEKORCRM_CONTRACTS_DIR", str(storage_root / "Договоры"))
    )
    estimates_dir = Path(
        os.environ.get("DEKORCRM_ESTIMATES_DIR", str(storage_root / "Сметы"))
    )
    uploads_dir = Path(
        os.environ.get("DEKORCRM_UPLOADS_DIR", str(storage_root / "uploads"))
    )

    return Settings(
        postgres_dsn=postgres_dsn,
        secret_key=os.environ.get(
            "DEKORCRM_WEB_SECRET_KEY", "change-me-before-production"
        ),
        admin_username=os.environ.get("DEKORCRM_WEB_USERNAME", "admin"),
        admin_password=os.environ.get("DEKORCRM_WEB_PASSWORD", "change-me"),
        storage_root=storage_root,
        contracts_dir=contracts_dir,
        estimates_dir=estimates_dir,
        uploads_dir=uploads_dir,
        web_host=os.environ.get("DEKORCRM_WEB_HOST", "127.0.0.1"),
        web_port=int(os.environ.get("DEKORCRM_WEB_PORT", "8000")),
    )
