# Environment And Paths

Currently detected live repo in the current session:
- `C:\Users\Aleks\YandexDisk-Gorodok198\СМЕТЫ НА ПРОВЕРКУ\CRM_OLD_BAD`

Previously observed path drift:
- older memory captured another repo location under `C:\Users\Aleks\YandexDisk-Gorodok198\...`;
- another office/home session also used `D:\Yandex.Disk\СМЕТЫ НА ПРОВЕРКУ\CRM_OLD_BAD`;
- the important invariant is still the repo folder name `CRM_OLD_BAD`, not the machine-specific parent path.

Operational implication:
- future sessions should verify the actual repo folder before assuming the environment path is correct;
- the user explicitly confirmed that work should happen only in `CRM_OLD_BAD`;
- office and home sessions must both treat this repo folder as the source of truth, even if the outer Yandex Disk root differs by machine.

Path-handling reminder for the application:
- prefer root-relative project paths;
- include repair logic for older stored absolute paths;
- warn when a workflow document is saved outside the project workspace because that is not reliably portable between office and home.

Current code-level protections:
- `CRM.py` and `smeta.py` both resolve stored document paths against the current workspace;
- startup health checks now warn about missing files and nonportable document paths;
- estimate PDF export now stores normalized project-relative paths when the file is saved inside the workspace.

Diagnostic tool:
- `portability_audit.py` inspects the current database for document-path portability and obvious path drift.

Server-side environment added on 2026-04-21:
- Ubuntu host: `130.49.129.245` (`Smetaserver`);
- server app mirror: `/opt/dekorcrm/app/CRM_OLD_BAD`;
- server storage root: `/opt/dekorcrm`;
- server database: PostgreSQL database `dekorcrm`.

Desktop/server bridge:
- `db_compat.py` lets the desktop apps switch from local SQLite to PostgreSQL when `DEKORCRM_POSTGRES_DSN` or `POSTGRES_DSN` is set;
- `launch_server_app.ps1` is the intended Windows launcher for secure desktop use through an SSH tunnel instead of opening PostgreSQL directly to the internet.
