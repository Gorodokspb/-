# Project Context

## Project

Desktop CRM and estimate generator for Dekorartstroy.

Main files:
- `CRM.py` - desktop CRM for counterparties, projects, documents, and finance
- `smeta.py` - estimate editor, draft autosave, PDF export, price list management
- `dekorart_base.db` - main SQLite database
- `dekorart_prices.db` - price list SQLite database

## What Was Done

### Environment

- Found working Python:
  - `C:\Users\CD86~1\AppData\Local\Programs\Python\Python313\python.exe`
- Installed dependencies:
  - `customtkinter`
  - `reportlab`
  - `openpyxl`
- Added `requirements.txt`
- Confirmed `CRM.py` and `smeta.py` pass `py_compile`
- Confirmed both apps start without immediate crash when launched through the full Python path

### Database / Permissions

- Found and fixed SQLite write issue for `dekorart_base.db`
- CRM startup was failing because SQLite could not write to the database
- After access fix, `CRM.py` starts correctly

### smeta.py

- Stabilized file storage:
  - estimate files are now tied to the project folder, not just current working directory
  - drafts and PDFs are organized under the local project folder
- Improved validation:
  - quantity and price validation added
  - PDF export now checks required fields and ensures at least one real work item exists
- Improved draft behavior:
  - draft file path adapts better when object name changes
- Improved Excel import:
  - clearer handling of duplicates
  - clearer handling of invalid rows
  - final import summary now shows inserted, duplicate, and skipped rows
- Removed some weak error handling and duplicate helper methods
- `smeta.py` import and startup smoke-test passed after changes

### CRM.py

- Reviewed for blocking issues
- No critical code-level blocker found after runtime environment was fixed
- Main next functional direction: document workflow, starting with Word contract integration

## Current State

- `smeta.py` is now more stable and runnable
- `CRM.py` is runnable
- Next business feature to implement in CRM:
  - Word contract integration
  - contract should pull data from client card and project card
  - future support for editable/selectable contract positions

## Known Technical Notes

- In this Codex environment, `python` may still not resolve by command name reliably
- Use full path when needed:

```powershell
C:\Users\CD86~1\AppData\Local\Programs\Python\Python313\python.exe CRM.py
C:\Users\CD86~1\AppData\Local\Programs\Python\Python313\python.exe smeta.py
```

- Install dependencies with:

```powershell
C:\Users\CD86~1\AppData\Local\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
```

## Next Step

Integrate Word contract template into CRM:
- load `.docx` contract template
- map placeholders to counterparty and project fields
- generate contract file for selected project
- prepare structure for editable contract sections/positions

## If You Resume Work Later

Tell Codex:
- read `PROJECT_CONTEXT.md`
- continue from Word contract integration in `CRM.py`

