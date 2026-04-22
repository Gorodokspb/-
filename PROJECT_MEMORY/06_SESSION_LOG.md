# Session Log

## 2026-04-20 - Memory System Bootstrapped

What happened:
- created a persistent multi-file memory system for the project;
- kept `PROJECT_CONTEXT.md` as legacy bootstrap context;
- established `PROJECT_MEMORY/` as the canonical long-term memory area;
- detected that the actual live repository currently available is `CRM_OLD_BAD`;
- noted a mismatch between the environment-reported project path and the path that actually exists on disk.

Why this matters:
- future sessions can resume from files instead of relying on chat history;
- important product and technical decisions now have dedicated places to live.

Follow-up:
- when the next real coding task starts, add a short session note with the task, files changed, behavior verified, and the next action.

## 2026-04-20 - Project Draft Recovery From CRM

Task:
- verify the live `estimate -> project -> CRM` chain and look for a continuity gap.

What was found:
- opening a project estimate from CRM depended on finding the managed draft file on disk;
- if the file was missing but the latest project draft still existed in `smeta_drafts`, the full estimate editor could reopen without the saved project draft state.

What changed:
- updated `smeta.py` so project estimate startup now falls back to the latest project draft stored in `smeta_drafts`;
- the fallback uses `project_id`, restores the payload from the database, and reconnects `current_draft_file` to the managed project draft path when available.

Verification:
- `python -m py_compile smeta.py` passed successfully.

Next action:
- manually verify the case where a project draft exists in the database but the expected draft file is missing or unavailable.

## 2026-04-20 - Counterparty Prefill From Project

Task:
- continue checking the `project -> counterparty -> contract` step for data-loss points.

What was found:
- when creating a new counterparty from a project, CRM preferred `counterparty_name` instead of the saved project customer;
- before a counterparty was attached, this could leave the form without the expected customer prefill even when the project already had customer data.

What changed:
- updated `CRM.py` so project details include `p.customer`;
- counterparty creation from a project now prefers customer data in this order: smeta payload -> project customer -> existing counterparty display name.

Verification:
- `python -m py_compile CRM.py` passed successfully.

Next action:
- manually verify that creating a counterparty from a project pre-fills the customer name before any counterparty is attached.

## 2026-04-20 - Contract Validation Guard

Task:
- inspect the contract generation path for cases where UI state and backend validation could disagree.

What was found:
- `generate_contract_for_project()` depended on `validate_counterparty_row_for_contract()`;
- if a project row existed without a linked counterparty, the row itself was still truthy, so validation could miss the "no counterparty attached" case unless UI buttons blocked the action first.

What changed:
- updated `CRM.py` so contract validation now explicitly checks `counterparty_id`;
- added a guard for missing counterparty type as well, so contract generation fails with a clear explanation instead of relying only on UI state.

Verification:
- `python -m py_compile CRM.py` passed successfully after the validation change.

Next action:
- manually verify that contract generation and contract settings both show a clear blocker when no counterparty is attached to the project.

## 2026-04-20 - Project Details Compatibility Fix

Task:
- continue searching for hidden regressions after adding `customer` access to project details.

What was found:
- `get_project_details()` is consumed in many places by positional indexes, not only by named keys;
- inserting `customer` into the middle of the SQL result shifted indexes and could break project-card actions and status rendering.

What changed:
- kept the original positional layout intact by moving `customer` to the end of the `get_project_details()` result;
- preserved named access through `project_row["customer"]` for the new counterparty prefill logic.

Verification:
- `python -m py_compile CRM.py` passed after restoring the compatible field order.

## 2026-04-20 - Contract Settings Header Clarified

Task:
- continue the review for smaller but confusing contract-flow issues.

What was found:
- the contract settings window title was hardcoded as if the customer were always a physical person.

What changed:
- the header now reflects the actual counterparty type or clearly states that no counterparty is attached yet.

Verification:
- `python -m py_compile CRM.py` passed after the UI text update.

## 2026-04-20 - Manual Document Path Normalization

Task:
- continue the review into project document handling and portability-sensitive path writes.

What was found:
- manual document creation in the project card inserted `file_path` into `documents` without passing it through workspace path normalization;
- this could preserve machine-specific absolute paths and break the home/office portability model.

What changed:
- updated manual document creation in `CRM.py` to store `file_path` through `to_workspace_storage_path()`.

Verification:
- `python -m py_compile CRM.py` passed after the change.

## 2026-04-20 - Project Deletion No Longer Removes Cash History

Task:
- continue the review into the finance model and check whether destructive actions match the shared-cash-desk rules.

What was found:
- deleting a project also deleted all linked rows from `cash_transactions`;
- this contradicted the agreed finance model where transactions belong to the shared cash desk and project tabs are only filtered views.

What changed:
- updated project deletion in `CRM.py` so linked cash transactions are detached from the project instead of being deleted;
- project documents are still deleted with the project;
- project events are cleaned up together with the project.

Verification:
- `python -m py_compile CRM.py` passed after the deletion-flow fix.

## 2026-04-20 - Finance Date Sorting Fixed

Task:
- continue the finance review for subtle data-quality problems in project and company cash views.

What was found:
- finance queries sorted `txn_date` as plain text in `DD.MM.YYYY` format;
- this could show operations in the wrong order across months and years.

What changed:
- updated finance queries in `CRM.py` to sort by year, month, and day parts instead of raw text order.

Verification:
- `python -m py_compile CRM.py` passed after the sorting fix.

## 2026-04-20 - CRM.py UTF-8 Text Restored After Mojibake Save

Task:
- inspect the user-reported broken CRM window where static labels appeared as `Р...` garbage text.

What was found:
- this was not a Python runtime failure;
- `CRM.py` had been saved with broken encoding and many Russian source literals turned into mojibake;
- dynamic values loaded from the database still displayed correctly, which helped confirm that the corruption lived in source text rather than in the UI toolkit or database.

What changed:
- restored `CRM.py` text by reversing the accidental single-byte recoding and writing the file back as UTF-8;
- kept the active uncommitted logic fixes in place while removing the mass text corruption;
- confirmed again that the working repository for this project is `CRM_OLD_BAD`.

Verification:
- `python -m py_compile CRM.py` passed after the UTF-8 restore;
- `git diff --word-diff=plain --unified=0 -- CRM.py` no longer shows mass replacement of Russian strings and now reflects only the intended live logic changes.

## 2026-04-20 - Contract Settings Now Sync Back Into Project Estimate

Task:
- continue the workflow review after the UTF-8 repair and look for the next logic bug in the project -> estimate -> contract chain.

What was found:
- contract number/date could diverge between project data and the estimate draft payload;
- after saving contract settings, the project row was updated, but the estimate draft could still keep an older contract label;
- if the user later saved the estimate again from the project card, the stale draft value could overwrite the newer contract data in the project.

What changed:
- `get_project_contract_context()` now prefers the project's saved contract/date when building the current contract context;
- added synchronization so `save_contract_settings()` also updates the linked estimate draft payload with the same contract label;
- in the project card estimate editor, the contract field now prefers the current project value before the draft payload value.

Verification:
- `python -m py_compile CRM.py smeta.py` passed after the fix.

## 2026-04-20 - Project Card No Longer Crashes On Counterparty Validation

Task:
- inspect the user-reported traceback when opening project workflow blocks from CRM.

What was found:
- `validate_counterparty_row_for_contract()` could receive a project row that had `counterparty_id` but did not include the counterparty field `type`;
- the function then accessed `counterparty_row["type"]` directly and raised `IndexError: No item with that key`.

What changed:
- updated `validate_counterparty_row_for_contract()` so it detects this project-row case;
- when only `counterparty_id` is available, it now loads the full counterparty row from the database before validating required contract fields;
- if the linked counterparty row is missing, the function now returns a clear blocker message instead of crashing.

Verification:
- `python -m py_compile CRM.py smeta.py` passed after the fix.

## 2026-04-20 - Manual Project Creation Stops Faking Customer Name

Task:
- continue the workflow review after the traceback fix and inspect manual project creation defaults.

What was found:
- when a project was created manually without a linked counterparty, the `customer` field was being filled with the project name/address itself;
- this made the project look as if a real customer was already known and could mislead later workflow checks and UI summaries.

What changed:
- manual project creation in `CRM.py` now keeps `customer` empty unless a real counterparty is selected.

Verification:
- `python -m py_compile CRM.py smeta.py` passed after the fix.

## 2026-04-20 - Project Workflow Status Model Expanded

Task:
- implement the new status logic requested during manual review of the project form.

What was found:
- the old model used only `В работе`, `Пауза`, and `Завершен`;
- this made estimate drafting and client agreement look the same as already approved live work.

What changed:
- added `Черновик` as the pre-agreement project stage;
- changed new project defaults in CRM and estimate-to-project creation to `Черновик`;
- normalized stored `Завершен` values to `Завершён`;
- updated project sorting so active work stays on top, then drafts, then paused, then completed;
- added status color support for `Черновик` and `Завершён`.

Verification:
- `python -m py_compile CRM.py smeta.py` passed after the status-model update.

## 2026-04-20 - Server And Browser Access Direction Clarified

Task:
- turn the user's server-hosting idea into a concrete product direction instead of leaving it as a vague infrastructure note.

What was found:
- the current product is a desktop `customtkinter` application backed by local SQLite files and document paths in the project folder;
- renting a server alone does not automatically create browser login/password access;
- true browser access for a tester means a web-facing layer with authentication, role separation, and centralized data/storage.

What changed:
- documented a separate staged web-deployment track in project memory;
- recorded that the target is a browser-accessible tester flow, while the existing desktop app remains the live operational version during transition.

Next action:
- use the staged plan in `PROJECT_MEMORY/13_WEB_DEPLOYMENT_PLAN.md` to choose architecture and define the first migration slice.

## 2026-04-20 - Web-Only Direction Confirmed

Task:
- confirm the final delivery model for shared access before starting architecture work.

What was confirmed:
- the user explicitly chose a true web version only;
- remote desktop on Linux or Windows must not be used as the product model.

What changed:
- upgraded the browser-access decision from a tentative direction to a confirmed project decision;
- aligned the deployment plan and next steps to web-only delivery.

Next action:
- define the first web architecture slice around authentication, projects, and a tester-safe browser workflow.

## 2026-04-21 - Browser MVP Deployed On Server

Task:
- turn the server preparation into a real browser entry point instead of only a database/storage backend.

What was done:
- added the `webapp/` FastAPI browser layer with session-based login, project list, project detail, and document download routes;
- added `run_web.py`, `.env.web.example`, and `WEB_SERVER_SETUP.md`;
- extended `requirements.txt` with FastAPI, Uvicorn, Jinja2, multipart support, and `itsdangerous`;
- uploaded the browser app to the Ubuntu server under `/opt/dekorcrm/app/CRM_OLD_BAD`;
- configured the runtime with `.env.web`, created the `dekorcrm-web` systemd service, and put Nginx in front of the app;
- copied server-side document storage into `/opt/dekorcrm/storage` and aligned document lookup with the new storage root.

Verification:
- the server returned live browser pages at `/login` and `/projects`;
- CSS and JS started loading correctly after fixing the Nginx/static handling;
- authenticated browser checks confirmed the project list and project detail pages load successfully.

Next action:
- continue improving the browser UX and then move estimate editing into the web interface.

## 2026-04-21 - Browser UI Redesigned

Task:
- replace the primitive browser MVP look with a more deliberate, cleaner interface that feels like a real operating dashboard.

What was done:
- redesigned `webapp/templates/projects.html` into a broader dashboard layout with a top operational bar, stronger hero section, cleaner metrics, and a more readable projects table;
- redesigned `webapp/templates/login.html` into a more polished access screen with infrastructure/value framing;
- redesigned `webapp/templates/project_detail.html` into a fuller project workspace with top controls, summary metrics, stronger document presentation, and a cleaner event timeline;
- expanded `webapp/static/app.css` to support the new visual system across login, list, and detail screens;
- redeployed the updated templates and styles to the server and restarted `dekorcrm-web`.

Verification:
- `python -m py_compile run_web.py webapp\\config.py webapp\\db.py webapp\\main.py webapp\\storage.py` passed;
- live server checks confirmed the new HTML structure and CSS classes are being served after redeploy;
- the new pages are available through the current browser URLs and may require a hard refresh in the client browser when cached.

Next action:
- continue with functional browser features, especially estimate editing and deeper project actions.

## 2026-04-21 - Contract Generation Now Promotes Draft Projects To In Progress

Task:
- continue strengthening the live desktop workflow instead of moving into web work yet.

What was found:
- the agreed project-stage model already had `Черновик -> В работе`, but the desktop CRM did not automatically move a project forward when the contract was successfully generated;
- this left the project in draft even after the workflow had already entered the contract/execution stage.

What changed:
- added `promote_project_to_in_progress_after_contract()` in `CRM.py`;
- after successful contract generation, the project now automatically moves from `Черновик` to `В работе`;
- manual statuses such as `Пауза` and `Завершён` are left untouched;
- the project history now records the automatic status transition.

Verification:
- `python -m py_compile CRM.py smeta.py` passed after the change.

Next action:
- manually verify the live scenario where a draft project generates its first contract and immediately appears as `В работе` in CRM.

## 2026-04-21 - Ubuntu Server Baseline Prepared And Data Imported To PostgreSQL

Task:
- begin real server preparation after the user rented an Ubuntu server and decided to centralize project storage there.

What was found:
- the rented server is Ubuntu 24.04 LTS with SSH access, about 8 GB RAM, and enough free disk space;
- the current desktop CRM cannot run there unchanged because it depends on `customtkinter` desktop UI and Word COM automation;
- however, the server is fully suitable as the central storage and database layer for the next architecture stage.

What changed:
- created and verified a non-root admin user `crmadmin`;
- enabled and verified `PostgreSQL`, `Nginx`, and `UFW` with SSH and Nginx access rules;
- uploaded `CRM_OLD_BAD` to `/opt/dekorcrm/app/CRM_OLD_BAD`;
- created a Python virtual environment in `/opt/dekorcrm/venv`;
- installed the project Python dependencies on the server;
- created a server-side backup archive of the uploaded project in `/opt/dekorcrm/backups/`;
- created PostgreSQL database `dekorcrm` and role `dekorcrm`;
- added `migrate_sqlite_to_postgres.py`;
- imported current data from `dekorart_base.db` and `dekorart_prices.db` into PostgreSQL.

Verification:
- server-side `python -m py_compile CRM.py smeta.py` passed inside the uploaded project;
- imported row counts in PostgreSQL match the SQLite source snapshot:
- `users`: 9
- `counterparties`: 2
- `projects`: 2
- `documents`: 1
- `project_events`: 10
- `smeta_drafts`: 35
- `cash_transactions`: 1
- `prices`: 138

Next action:
- decide how the desktop CRM should talk to centralized server data next: PostgreSQL adapter inside the app, or a dedicated server API layer.

## 2026-04-20 - Office/Home Portability Audit And Memory Upgrade

Task:
- shift priority away from the paused web track and verify that office/home desktop work keeps saving portable document paths;
- strengthen persistent memory so future office and home sessions can resume without retelling prior work.

What was found:
- the current office workspace is `D:\Yandex.Disk\СМЕТЫ НА ПРОВЕРКУ\CRM_OLD_BAD`;
- the database currently stores document paths in `documents` as relative project paths, and the recent saved estimate document resolved correctly in the current workspace;
- `smeta_drafts` and `project_events` did not contain explicit drive-letter or workspace-root path strings in the current data snapshot;
- `CRM.py` already had repair logic for old document paths, but project-card PDF export still wrote the selected PDF path back to `documents` directly instead of normalizing it first;
- both apps could still let a user save PDFs outside the project workspace, which is a portability risk when switching between office and home.

What changed:
- added `is_workspace_portable_path()` to both `CRM.py` and `smeta.py`;
- upgraded startup health checks in both apps so they warn not only about missing files but also about nonportable document paths;
- updated project-card estimate PDF export in `CRM.py` so the saved PDF path is normalized before writing back into `documents`;
- updated estimate PDF export in `smeta.py` to warn when a PDF is saved outside the project workspace;
- added `portability_audit.py` as a reusable database audit tool for office/home path checks;
- updated project memory to reflect that the web track is paused and office/home continuity is now the active priority;
- added `PROJECT_MEMORY/14_HOME_OFFICE_CONTINUITY.md` and updated the memory entry point, next steps, decisions, environment notes, and conversation rules.

Verification:
- `py portability_audit.py` reported zero absolute paths in the current `documents` rows and no explicit drive/workspace hints in `smeta_drafts` or `project_events`;
- `py -m py_compile CRM.py smeta.py portability_audit.py` passed successfully.

Next action:
- manually test estimate PDF export from both CRM and the estimate editor, once saving inside the workspace and once outside it, and confirm that the warnings and saved document paths behave as expected.

## 2026-04-21 - Server PostgreSQL Bridge For Desktop CRM

Task:
- prepare the rented Ubuntu server as the central data/storage side for the CRM project;
- keep the desktop Windows workflow, but make the app able to switch from local SQLite to server PostgreSQL safely.

What was done:
- verified the Ubuntu server baseline under `crmadmin`: PostgreSQL active, Nginx active, UFW active, project files uploaded under `/opt/dekorcrm/app/CRM_OLD_BAD`;
- created and verified PostgreSQL database `dekorcrm`, then migrated current SQLite data into PostgreSQL tables (`users`, `counterparties`, `projects`, `documents`, `project_events`, `smeta_drafts`, `cash_transactions`, `prices`);
- added `migrate_sqlite_to_postgres.py` as the repeatable migration script;
- added `db_compat.py` as a compatibility bridge so the app can keep its current SQL flow but switch backend to PostgreSQL when `DEKORCRM_POSTGRES_DSN` or `POSTGRES_DSN` is set;
- updated `CRM.py` and `smeta.py` to route their local `sqlite3.connect(...)` calls through the compatibility layer without rewriting the full application logic yet;
- updated health checks so they stop requiring local `.db` files when the app is intentionally running against PostgreSQL;
- added `launch_server_app.ps1` so Windows can launch `CRM.py` or `smeta.py` through a local SSH tunnel to the server database without exposing PostgreSQL directly to the public internet;
- added `psycopg[binary]` to `requirements.txt`.

Verification:
- local compile passed: `python -m py_compile CRM.py smeta.py db_compat.py migrate_sqlite_to_postgres.py`;
- server compile passed inside `/opt/dekorcrm/app/CRM_OLD_BAD`;
- live smoke test against server PostgreSQL passed through `db_compat.py`: translated `sqlite_master`, `PRAGMA table_info(projects)`, and `SELECT COUNT(*) FROM projects` all returned valid results.

Important note:
- at this stage PostgreSQL remains safely reachable through local/server-side access and SSH tunneling; direct public port exposure was not required.

## 2026-04-22 - Browser Estimate Editor Workflow Added And Synced

Task:
- move the browser version from a read-only project viewer to the first real editable estimate workflow.

What was done:
- expanded the FastAPI browser layer so projects now have a dedicated estimate route: `/projects/{id}/estimate`;
- added estimate read/write logic in `webapp/db.py` for loading estimate payloads from `smeta_drafts` and server draft files;
- added estimate draft save logic back into PostgreSQL and server storage;
- added server-storage helpers in `webapp/storage.py` for managed estimate draft paths;
- added `webapp/templates/estimate_editor.html` as the first real browser estimate editor screen;
- added `webapp/static/estimate_editor.js` for browser-side row creation, editing, deletion, total recalculation, and discount recalculation;
- updated `webapp/static/app.css` to support the estimate editor layout and controls;
- updated the project detail page to link directly into the browser estimate workflow.

Verification:
- local `python -m py_compile run_web.py webapp\\config.py webapp\\db.py webapp\\main.py webapp\\storage.py` passed;
- the updated files were uploaded to the server under `/opt/dekorcrm/app/CRM_OLD_BAD`;
- `dekorcrm-web` was restarted successfully and confirmed `active`;
- browser HTTP checks confirmed the estimate route loads and a save POST redirects to `?saved=1`.

Persistence and sync state:
- local repo was committed as `e76391b` (`Add browser estimate editor workflow`);
- GitHub `origin/master` was updated to the same commit;
- server repo under `/opt/dekorcrm/app/CRM_OLD_BAD` was reset to `origin/master`;
- local repo, GitHub, and server were aligned to the same commit at the end of the session.

Next action:
- improve the browser estimate UX and choose the next functional slice: web PDF export or deeper browser-side project editing.

## 2026-04-22 - Browser Estimate UX Improved

Task:
- make the first browser estimate editor noticeably more comfortable for real use instead of keeping it only technically functional.

What was done:
- expanded the estimate screen with a clearer current-selection panel;
- added browser-side search across estimate rows;
- added row-type filters for all rows, sections only, and positions only;
- added row duplication;
- added row move up/down controls;
- added clear-selection behavior;
- added an unsaved-changes badge and browser unload protection while the form is dirty;
- enabled double-click row editing in the estimate table.

Verification:
- local `python -m py_compile run_web.py webapp\\config.py webapp\\db.py webapp\\main.py webapp\\storage.py` passed;
- updated template, CSS, and JavaScript were uploaded to the server;
- `dekorcrm-web` was restarted and confirmed `active`;
- HTTP check against `/projects/7/estimate` confirmed the new search, selection, duplication, and reorder controls are present in the served page.

Next action:
- continue with the next browser estimate slice: PDF export or deeper project linkage.

## 2026-04-22 - Web Estimate PDF Export Added

Task:
- finish the next browser estimate milestone by generating a real PDF directly from the web editor and serving it through the browser flow.

What was done:
- added `webapp/estimate_pdf.py` with ReportLab-based estimate PDF generation;
- extended `webapp/storage.py` so browser estimates now have a dedicated PDF path in server storage;
- rewrote `webapp/main.py` cleanly and added a `POST /projects/{id}/estimate/pdf` route;
- made the web estimate form save the current browser state before PDF generation;
- added a `Сформировать PDF` button to the estimate editor and kept the existing download links;
- uploaded the updated files to the server and restarted `dekorcrm-web`.

Verification:
- local `python -m py_compile run_web.py webapp\\config.py webapp\\db.py webapp\\main.py webapp\\storage.py webapp\\estimate_pdf.py` passed;
- server-side `python3 -m py_compile webapp/main.py webapp/storage.py webapp/estimate_pdf.py` passed inside `/opt/dekorcrm/app/CRM_OLD_BAD`;
- `dekorcrm-web` restarted successfully and remained `active`;
- live browser check confirmed the estimate page shows the new `Сформировать PDF` action;
- live server-side generation created a PDF for project `7`, and the estimate page now exposes the `Скачать PDF` link.

Next action:
- continue from PDF export into the deeper browser estimate workflow: better table ergonomics, project linkage, and then browser-side project editing.
