# Next Steps

Current immediate priorities:
1. Use this memory system as the standard starting point for every new Codex session.
2. Manually verify CRM -> project estimate reopening when the draft exists in `smeta_drafts` but the managed file is missing.
3. Manually verify that project -> create counterparty pre-fills the customer name before a counterparty is attached.
4. Manually verify that contract generation is blocked with a clear message when no counterparty is attached.
5. Manually verify that project card actions still use the correct project fields after restoring `get_project_details()` index compatibility.
6. Manually verify that deleting a project detaches linked cash operations instead of deleting them.
7. Manually verify that finance tabs and project finance blocks sort operations correctly across different months.
8. Continue fixing real workflow bugs found in manual testing and screenshots.
9. Run a full live flow: estimate -> project -> counterparty -> contract.
10. Validate portability between home and office path setups.
11. After the workflow is stable, implement the shared cash desk model.
12. Manually verify that after saving contract settings, reopening or re-saving the estimate does not roll the contract number/date back to an older draft value.
13. Manually verify that opening a project card with a linked counterparty no longer throws `No item with that key`.
14. Manually verify that a manually created project without a counterparty no longer displays its own address/name as the customer.
15. Manually verify the new project-stage rules: new projects start in `Черновик`, approved projects move to `В работе`, and completed projects display as `Завершён`.

16. Choose the web-delivery architecture for the future server version using `PROJECT_MEMORY/13_WEB_DEPLOYMENT_PLAN.md`.
17. Define the first browser MVP slice: login, project list, project card summary, and read-only tester access.
18. Keep the current desktop CRM as the operational version until the browser MVP is real and testable.
19. Treat remote desktop options as rejected and design only for browser delivery.

Before the next coding session:
- continue work only in `CRM_OLD_BAD`;
- treat any environment path pointing to another folder name as stale until the real disk path is verified.
- before ending the session, remind the user to later test the home/office portability setup live.

What to update after the next task:
- add a new session entry;
- move completed items out of this file;
- write down any new blocker immediately.
