# Architecture And Data

Code ownership:
- `CRM.py` owns the CRM shell and project lifecycle.
- `smeta.py` owns estimate editing and price list operations.

Intentional split:
- the CRM and estimate modules are separated on purpose;
- `smeta.py` should not be treated as obsolete unless the team explicitly retires it.

Storage model:
- code and templates live in GitHub;
- working data lives in the project folder on Yandex Disk;
- SQLite databases, Office files, PDFs, and generated documents remain local working artifacts rather than normal git-tracked assets.

Path strategy:
- avoid hard dependency on absolute machine-specific paths;
- saved references should be relative to the project root when possible;
- older absolute paths should be repairable against the current workspace root.

Portability requirement:
- the app must work both at home and in the office even if the Yandex Disk root differs.

Architectural caution:
- path correctness is a product feature in this project, not a small implementation detail.
