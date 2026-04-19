# Next Steps

Current immediate priorities:
1. Use this memory system as the standard starting point for every new Codex session.
2. Manually verify CRM -> project estimate reopening when the draft exists in `smeta_drafts` but the managed file is missing.
3. Manually verify that project -> create counterparty pre-fills the customer name before a counterparty is attached.
4. Manually verify that contract generation is blocked with a clear message when no counterparty is attached.
5. Manually verify that project card actions still use the correct project fields after restoring `get_project_details()` index compatibility.
6. Continue fixing real workflow bugs found in manual testing and screenshots.
7. Run a full live flow: estimate -> project -> counterparty -> contract.
8. Validate portability between home and office path setups.
9. After the workflow is stable, implement the shared cash desk model.

Before the next coding session:
- confirm whether `CRM_OLD_BAD` is still the active repo name or whether the working project moved to another folder;
- if the repo folder name changed, update `MEMORY.md` and `11_ENVIRONMENT_AND_PATHS.md`.

What to update after the next task:
- add a new session entry;
- move completed items out of this file;
- write down any new blocker immediately.
