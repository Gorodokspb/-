import uvicorn

from webapp.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "webapp.main:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
