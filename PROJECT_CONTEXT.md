# PROJECT_CONTEXT

## Project

Working title:
- CRM and estimate workflow for Dekorartstroy.

Core files:
- `CRM.py` - main CRM app: projects, counterparties, documents, finance screens, and entry points into estimate work.
- `smeta.py` - active estimate editor and price list manager. This is still a working tool, not a dead legacy file.
- `dekorart_base.db` - main SQLite database for projects, documents, counterparties, and related records.
- `dekorart_prices.db` - separate SQLite database for the price list.
- `contract_template_physical.docx` - current contract template.

GitHub:
- `https://github.com/Gorodokspb/-.git`

Branch:
- `master`


## Source Of Truth

Current working model:
- code lives in GitHub;
- working databases, estimates, contracts, PDFs, and office files live in the project folder on Yandex Disk;
- the app must work both at home and in the office even if the Yandex Disk path is different on each PC.

Important conclusion from recent work:
- the main failure was not missing saves;
- the real problem was stale absolute paths stored inside the local data layer;
- code has been moved toward path handling relative to the project folder, with repair logic for older saved paths.

Current truth:
- `CRM.py` is the main CRM shell and project workflow;
- `smeta.py` is still the real estimate and price list tool used in daily work.


## Product Flow

The agreed business flow is:
1. Create estimate.
2. Create project from the estimate.
3. Create or attach counterparty.
4. Generate contract.
5. Continue project execution through documents and finance.

Key rule:
- work starts from the estimate, not from the counterparty.


## Architecture Decisions

### Estimate First

The estimate is the first-class entry point of the deal.
It is not a side utility.
It is the starting state that later feeds the project, counterparty, and contract steps.

### CRM + Estimate Split

Current split is intentional:
- `CRM.py` owns the CRM shell and project lifecycle;
- `smeta.py` owns estimate editing and price list operations.

### Storage Model

Current storage model is:
- GitHub for code and templates;
- Yandex Disk for working data and generated files.

Do not try to put all working data into plain Git.
SQLite files, Office files, PDFs, and other binaries should stay outside normal Git history.

### Path Strategy

The app should avoid hard dependency on absolute machine-specific paths.
Saved paths should be relative or repairable from the current workspace root.


## Confirmed Product Rules

### Project And Contract Order

The correct order is:
- estimate;
- project;
- counterparty;
- contract.

Counterparty creation can happen after estimate work.
Contract generation depends on valid project, estimate, and counterparty data.

### Price List

Current expected behavior:
- Excel import must not create duplicate rows for the same work name;
- if a work already exists and price or unit changed, the existing row should be updated;
- if the existing row is already current, it should be skipped;
- an estimate row added from the price list should keep a reference to the source price row;
- when editing that estimate row, the user can choose to push the changed price back into the price list.

### Finance / Cash Desk Direction

The planned finance model is:
- one shared cash desk as the source of truth;
- every income or expense can optionally be linked to a project at creation time;
- project finance screens should show filtered views of the same shared operations;
- no duplicate finance entries should be created inside project tabs.

This direction is accepted, but not fully implemented yet.


## Recent Technical Work

### Home / Office Reliability

- path handling was improved to be more portable across different PCs;
- old saved document paths can be repaired against the current project workspace;
- the app should be more stable when the same folder is opened from different Yandex Disk root paths.

### UI And Windowing

- window positioning and sizing were adjusted for real user screens;
- some forms were made more scrollable and screen-friendly;
- duplicated labels in the sidebar and project cards were reduced.

### Copy / Paste Support

Text fields now need to support:
- `Ctrl+C`
- `Ctrl+V`
- `Ctrl+X`
- `Ctrl+A`
- `Delete`
- right-click context menu actions

This especially matters in estimate search fields and project forms.

### Estimate UX Fixes

Recent fixes focused on:
- quick search reacting immediately after paste;
- proper clipboard behavior in estimate search fields;
- better bottom action bar layout in the estimate window;
- rounding and normalization of totals to avoid floating-point artifacts.

### Price List Access

The price list should be reachable:
- from inside the estimate editor;
- directly from the CRM sidebar.

The user should not need to enter a project and then enter estimate mode just to update prices.

### Excel Import Window

The Excel file picker for price import must open as a proper child flow of the price manager window.
It should not hide behind the price manager and block interaction.


## Things That Still Need Real Manual Testing

These must be checked on live UI runs:
- CRM opening on the user screen size;
- project card opening and fit on screen;
- estimate editor opening from a project;
- direct price list opening from CRM;
- Excel import into the price list;
- `Ctrl+V` in estimate search fields;
- immediate search refresh after paste;
- bottom estimate buttons staying visible;
- contract generation against the real Word template.

Also validate with a real workflow:
- office save -> home reopen;
- price update import -> estimate add/edit -> save back to price list;
- estimate -> project -> counterparty -> contract end-to-end flow.


## What Not To Do Right Now

Do not spend time on:
- large refactor of all `CRM.py`;
- rebuilding the whole estimate architecture from scratch;
- moving all working data into GitHub;
- deep database migration without real need;
- broad cosmetic redesign unrelated to active workflow pain.


## Current Priority

Current priority is:
1. keep the live workflow stable;
2. finish manual bug fixes found from real user screenshots;
3. validate the full path from estimate to contract;
4. then move to the shared cash desk implementation.


## Next Step

Next practical step:
1. finish remaining UI bugs found in manual testing;
2. run a full real-object flow: estimate -> project -> counterparty -> contract;
3. then implement the shared cash desk model without duplicated project finance entries.
