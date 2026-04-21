# Next Steps

Current immediate priorities:
1. Use this memory system and the office/home continuity file as the standard starting point for every new Codex session.
2. Manually verify portability between office and home path setups using the current Yandex Disk workspace.
3. Run `portability_audit.py` before or after switching machines if there is any doubt about saved document paths.
4. Manually verify that estimate PDF export from both `CRM.py` and `smeta.py` stays portable when the file is saved inside the project workspace.
5. Manually verify that the new warning appears if a PDF is saved outside the project workspace.
6. Manually verify CRM -> project estimate reopening when the draft exists in `smeta_drafts` but the managed file is missing.
7. Manually verify that project -> create counterparty pre-fills the customer name before a counterparty is attached.
8. Manually verify that contract generation is blocked with a clear message when no counterparty is attached.
9. Manually verify that project card actions still use the correct project fields after restoring `get_project_details()` index compatibility.
10. Manually verify that deleting a project detaches linked cash operations instead of deleting them.
11. Manually verify that finance tabs and project finance blocks sort operations correctly across different months.
12. Run a full live flow: estimate -> project -> counterparty -> contract.
13. Continue fixing real workflow bugs found in manual testing and screenshots.
14. After the workflow is stable, implement the shared cash desk model.
15. Manually verify that after saving contract settings, reopening or re-saving the estimate does not roll the contract number/date back to an older draft value.
16. Manually verify that opening a project card with a linked counterparty no longer throws `No item with that key`.
17. Manually verify that a manually created project without a counterparty no longer displays its own address/name as the customer.
18. Manually verify the new project-stage rules: new projects start in `Черновик`, successful contract generation moves them into `В работе`, and completed projects display as `Завершён`.

Paused for now:
- the web/browser delivery track is paused until desktop workflow stability and office/home continuity are confirmed live.

Before the next home session:
- continue work only in `CRM_OLD_BAD`;
- treat any environment path pointing to another folder name as stale until the real disk path is verified;
- read `MEMORY.md`, `PROJECT_MEMORY/00_INDEX.md`, `PROJECT_MEMORY/07_NEXT_STEPS.md`, `PROJECT_MEMORY/14_HOME_OFFICE_CONTINUITY.md`, and `PROJECT_MEMORY/06_SESSION_LOG.md`;
- if the app warns about nonportable or missing document paths, resolve that before continuing normal workflow.

What to update after the next task:
- add a new session entry with the machine context (`office` or `home`);
- move completed items out of this file;
- write down any new blocker immediately.
