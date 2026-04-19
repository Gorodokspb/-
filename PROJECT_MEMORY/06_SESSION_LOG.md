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
