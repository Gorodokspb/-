# Next Steps

Current immediate priorities:
1. Use this memory system as the standard starting point for every new Codex session.
2. Confirm that the local repo, GitHub, and server still match the latest PDF-export commit before starting the next large code change.
3. Manually verify the full live browser estimate flow: login -> projects -> project card -> web estimate -> add section -> add items -> save -> reopen -> generate PDF -> download PDF.
4. Improve the browser estimate UX so it feels production-ready instead of only technically working.
5. Continue with the next browser slice after PDF export:
6. Option A: browser-side project editing and tighter estimate/project linkage.
7. Option B: richer estimate actions such as inline row editing, section totals visibility, and stronger validation.
8. Keep fixing real workflow bugs found in manual testing and screenshots.
9. Continue preserving office/home continuity and avoid machine-specific path regressions.
10. Keep the desktop/server PostgreSQL bridge working until the browser flow can replace more of the daily routine.

Highest-value short-term browser tasks:
1. Improve the estimate/project linkage so document state and project updates are clearer from the estimate screen.
2. Continue smoothing estimate row editing where friction still appears in live use.
3. Add clearer linked-document visibility from the estimate screen.
4. Add stronger validation around customer, contract, and estimate totals before final export.
5. Continue visual cleanup only where it helps daily work speed.

Desktop and data integrity checks that still matter:
1. Manually verify desktop launch through `launch_server_app.ps1` with the server PostgreSQL backend enabled.
2. Manually verify portability between office and home path setups using the current Yandex Disk workspace.
3. Run `portability_audit.py` before or after switching machines if there is any doubt about saved document paths.
4. Manually verify that estimate PDF export from both `CRM.py` and `smeta.py` stays portable when the file is saved inside the project workspace.
5. Manually verify that the new warning appears if a PDF is saved outside the project workspace.

Broader workflow checks still pending:
1. Run a full live flow: estimate -> project -> counterparty -> contract.
2. Manually verify that project -> create counterparty pre-fills the customer name before a counterparty is attached.
3. Manually verify that contract generation is blocked with a clear message when no counterparty is attached.
4. Manually verify that deleting a project detaches linked cash operations instead of deleting them.
5. Manually verify that finance tabs and project finance blocks sort operations correctly across different months.

Before the next work block:
- continue work only in `CRM_OLD_BAD`;
- treat any environment path pointing to another folder name as stale until the real disk path is verified;
- if the server web UI looks outdated, hard refresh the browser before assuming deployment failed;
- update `PROJECT_MEMORY/06_SESSION_LOG.md` right after any meaningful completed task.
- remember that the browser estimate page now supports both draft save and direct PDF generation.
