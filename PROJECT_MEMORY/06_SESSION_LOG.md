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
