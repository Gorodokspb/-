# Environment And Paths

Current live repo in this session:
- `C:\Users\Aleks\YandexDisk-Gorodok198\СМЕТЫ НА ПРОВЕРКУ\CRM_OLD_BAD`

Important invariant:
- the real source of truth is the folder `CRM_OLD_BAD`;
- do not trust older environment hints if they point to another folder name;
- office and home sessions may have different outer disk roots, but the repo folder name and project contents must stay aligned.

Path-handling reminder for the application:
- prefer root-relative project paths;
- include repair logic for older stored absolute paths;
- warn when a workflow document is saved outside the project workspace because that is not reliably portable between office and home.

Current code-level protections:
- `CRM.py` and `smeta.py` both resolve stored document paths against the current workspace;
- startup health checks warn about missing files and nonportable document paths;
- estimate PDF export stores normalized project-relative paths when the file is saved inside the workspace;
- `portability_audit.py` remains the lightweight audit tool for path portability.

Server-side environment:
- Ubuntu host: `130.49.129.245` (`Smetaserver`);
- server app mirror: `/opt/dekorcrm/app/CRM_OLD_BAD`;
- server storage root: `/opt/dekorcrm/storage`;
- server database: PostgreSQL database `dekorcrm`;
- browser app service: `dekorcrm-web`;
- reverse proxy: Nginx.

Desktop/server bridge:
- `db_compat.py` lets the desktop apps switch from local SQLite to PostgreSQL when `DEKORCRM_POSTGRES_DSN` or `POSTGRES_DSN` is set;
- `launch_server_app.ps1` is the intended Windows launcher for secure desktop use through an SSH tunnel instead of exposing PostgreSQL directly to the internet.

Current synchronized state:
- local repo was clean at the end of the last session;
- GitHub `origin/master` and local `master` were aligned on commit `e76391b`;
- the server repo under `/opt/dekorcrm/app/CRM_OLD_BAD` was also reset to `e76391b`;
- `dekorcrm-web` was restarted and confirmed active after deployment of the web estimate editor.
