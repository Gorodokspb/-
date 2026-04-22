# Project Memory Entry Point

This file is the first stop for restoring context in a new Codex session.

If we continue work later, read these files in this order:
1. `PROJECT_MEMORY/00_INDEX.md`
2. `PROJECT_MEMORY/01_PROJECT_SNAPSHOT.md`
3. `PROJECT_MEMORY/07_NEXT_STEPS.md`
4. `PROJECT_MEMORY/14_HOME_OFFICE_CONTINUITY.md`
5. `PROJECT_MEMORY/06_SESSION_LOG.md`
6. `PROJECT_MEMORY/09_BUGS_AND_RISKS.md`

Fast summary:
- Project: Dekorartstroy CRM + estimate workflow.
- Main app shell: `CRM.py`
- Active estimate tool: `smeta.py`
- Active browser layer: `webapp/` + `run_web.py`
- Main DB: `dekorart_base.db`
- Price DB: `dekorart_prices.db`
- Contract template: `contract_template_physical.docx`
- Diagnostic script for office/home portability: `portability_audit.py`
- Current repo path detected in this session: `C:\Users\Aleks\YandexDisk-Gorodok198\СМЕТЫ НА ПРОВЕРКУ\CRM_OLD_BAD`
- Server browser entry points: `/login`, `/projects`, `/projects/{id}`, `/projects/{id}/estimate`
- Latest synced git commit after the browser estimate work: `e76391b` (`Add browser estimate editor workflow`)

Important working rule:
- The estimate is the start of the business flow.
- The accepted order is estimate -> project -> counterparty -> contract.
- The browser/web track is active again through the server-hosted MVP and now includes the first editable web estimate screen, while desktop continuity still remains important.

Operational rule for future sessions:
- Update `PROJECT_MEMORY/06_SESSION_LOG.md` after meaningful work.
- Update `PROJECT_MEMORY/07_NEXT_STEPS.md` whenever priorities change.
- Update `PROJECT_MEMORY/05_DECISIONS.md` when a product or technical decision becomes stable.
- Read `PROJECT_MEMORY/14_HOME_OFFICE_CONTINUITY.md` before resuming work on another machine.
- Keep `PROJECT_CONTEXT.md` as legacy bootstrap context, but treat `PROJECT_MEMORY/` as the canonical long-term memory system.
