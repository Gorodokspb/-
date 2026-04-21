# Next Steps

Current immediate priorities:
1. Use this memory system and the office/home continuity file as the standard starting point for every new Codex session.
2. Confirm the full live Windows flow against server PostgreSQL: login -> open project -> open estimate -> save estimate -> view documents.
3. Continue fixing real workflow bugs found in manual testing and screenshots.
4. Move estimate work into the browser with a real web editor instead of the current read-only/project-summary MVP.
5. Manually verify portability between office and home path setups using the current Yandex Disk workspace.
6. Run `portability_audit.py` before or after switching machines if there is any doubt about saved document paths.
7. Manually verify that estimate PDF export from both `CRM.py` and `smeta.py` stays portable when the file is saved inside the project workspace.
8. Manually verify that the new warning appears if a PDF is saved outside the project workspace.
9. Manually verify CRM -> project estimate reopening when the draft exists in `smeta_drafts` but the managed file is missing.
10. Manually verify that project -> create counterparty pre-fills the customer name before a counterparty is attached.
11. Manually verify that contract generation is blocked with a clear message when no counterparty is attached.
12. Manually verify that project card actions still use the correct project fields after restoring `get_project_details()` index compatibility.
13. Manually verify that deleting a project detaches linked cash operations instead of deleting them.
14. Manually verify that finance tabs and project finance blocks sort operations correctly across different months.
15. Run a full live flow: estimate -> project -> counterparty -> contract.
16. After the workflow is stable, implement the shared cash desk model.
17. Manually verify that after saving contract settings, reopening or re-saving the estimate does not roll the contract number/date back to an older draft value.
18. Manually verify that opening a project card with a linked counterparty no longer throws `No item with that key`.
19. Manually verify that a manually created project without a counterparty no longer displays its own address/name as the customer.
20. Manually verify the new project-stage rules: new projects start in `Черновик`, successful contract generation moves them into `В работе`, and completed projects display as `Завершён`.
21. Manually verify desktop launch through `launch_server_app.ps1` with the server PostgreSQL backend enabled.
22. Decide whether to keep the secure SSH-tunnel desktop model or later add a fuller web/API layer.
23. Replace or redesign Word COM based contract generation for Linux-compatible server operation.

Before the next home session:
- continue work only in `CRM_OLD_BAD`;
- treat any environment path pointing to another folder name as stale until the real disk path is verified;
- read `MEMORY.md`, `PROJECT_MEMORY/00_INDEX.md`, `PROJECT_MEMORY/07_NEXT_STEPS.md`, `PROJECT_MEMORY/14_HOME_OFFICE_CONTINUITY.md`, and `PROJECT_MEMORY/06_SESSION_LOG.md`;
- if the app warns about nonportable or missing document paths, resolve that before continuing normal workflow.
- if the server web UI looks outdated, hard refresh the browser before assuming deployment failed.

What to update after the next task:
- add a new session entry with the machine context (`office` or `home`);
- move completed items out of this file;
- write down any new blocker immediately.
