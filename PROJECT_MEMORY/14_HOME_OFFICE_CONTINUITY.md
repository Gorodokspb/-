# Home And Office Continuity

Purpose:
- keep the desktop CRM workflow reliable across office and home without re-explaining recent work;
- make sure saved drafts, PDFs, and project documents stay portable between machines.

Start-of-session checklist on another machine:
1. Confirm the real repo path on disk and keep working only in `CRM_OLD_BAD`.
2. Read `MEMORY.md`.
3. Read `PROJECT_MEMORY/00_INDEX.md`.
4. Read `PROJECT_MEMORY/07_NEXT_STEPS.md`.
5. Read `PROJECT_MEMORY/14_HOME_OFFICE_CONTINUITY.md`.
6. Read `PROJECT_MEMORY/06_SESSION_LOG.md`.

Document storage rules:
- save workflow files inside the project workspace whenever possible;
- if a file is saved outside the project workspace, treat that as nonportable until proven otherwise;
- when the app warns about a nonportable path, fix that before switching machines.

Verification rule:
- before or after switching between office and home, run `py portability_audit.py`;
- if the audit or startup health check reports missing or nonportable document paths, record the finding in session memory and repair it before continuing normal work.

Memory rule:
- after each meaningful task, add a session note with machine context, what changed, what was verified, and what still needs testing;
- when priorities change, update `07_NEXT_STEPS.md` and `05_DECISIONS.md` in the same session.

Current priority:
- the browser/web track is paused;
- reliable office/home desktop continuity is the active focus.
