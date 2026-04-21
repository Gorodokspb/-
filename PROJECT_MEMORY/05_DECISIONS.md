# Confirmed Decisions

## D-001 Estimate First

Status:
- accepted

Decision:
- the estimate is the primary entry point into the workflow.

Reason:
- this matches the real business process and avoids forcing users to create counterparties too early.

## D-002 CRM And Estimate Split Stays For Now

Status:
- accepted

Decision:
- `CRM.py` remains the CRM shell and `smeta.py` remains the active estimate and price tool.

Reason:
- this reflects current real usage and avoids risky refactors while the workflow is still evolving.

## D-003 Working Data Stays Out Of Normal Git History

Status:
- accepted

Decision:
- databases, contracts, PDFs, estimates, and other working binaries stay in the Yandex Disk project folder rather than being treated as normal source-controlled assets.

Reason:
- the repo should track code and templates, while operational data remains local and synchronized through Yandex Disk.

## D-004 Path Handling Must Be Portable

Status:
- accepted

Decision:
- the app should rely on relative or repairable paths instead of fixed machine-specific absolute paths.

Reason:
- the same project folder is used across home and office environments with different root locations.

## D-005 Shared Cash Desk Is The Finance Target

Status:
- accepted direction, not fully implemented

Decision:
- finance should converge toward one shared cash desk with optional project linkage and filtered project views.

Reason:
- this avoids duplicating operations while still supporting project-level finance visibility.

Implementation note:
- deleting a project must not delete cash transactions themselves;
- project-linked transactions should stay in the shared cash desk and lose only the project linkage.

## D-006 Python Source With Russian UI Text Must Stay UTF-8

Status:
- accepted

Decision:
- Python source files that contain Russian UI strings must be stored and edited in UTF-8 without accidental single-byte recoding.

Reason:
- a stray save with the wrong encoding can turn static interface text into mojibake while leaving the code executable, which makes the app look broken and is expensive to clean up manually.

## D-007 Project Statuses Must Reflect Real Workflow Stage

Status:
- accepted

Decision:
- project statuses are now:
- `Черновик` for estimate preparation and client agreement;
- `В работе` after agreement when the team moves into contract, execution, payments, and live delivery;
- `Пауза` for temporarily stopped but still active work;
- `Завершён` for closed finished projects.

Reason:
- the old three-status model mixed pre-sale estimate work with active execution and made CRM stages less informative.

## D-008 Browser Access Is A Separate Delivery Target

Status:
- accepted and active as a staged MVP

Decision:
- the project will move toward a real web version with browser login/password access on a rented server;
- remote desktop on Linux or Windows is explicitly out of scope as a delivery model;
- the current `customtkinter` desktop application remains the live working version until the web path is designed and delivered in stages.

Reason:
- the user wants a colleague to open the system through a browser, test the ready version, and send feedback without editing code;
- this requires a web-facing layer with authentication and role control, which is meaningfully different from hosting a Windows desktop session.

Implementation note:
- do not promise "site access" by only moving the current app to a server;
- first stabilize the live desktop workflow, then extract the data model and build a minimal browser-accessible surface.
- the first minimal browser-accessible surface now exists on the server using FastAPI templates, session auth, PostgreSQL, and Nginx.

## D-009 Office And Home Continuity Takes Priority

Status:
- accepted

Decision:
- the immediate priority is reliable desktop work from both office and home using the shared Yandex Disk project folder;
- portability, path safety, and durable session memory stay important even while the browser MVP is being developed.

Reason:
- the user needs to continue work across office and home without re-explaining prior work or losing access to saved estimates, PDFs, drafts, and related project documents.

Implementation note:
- save workflow files inside the project workspace whenever possible;
- treat warnings about nonportable document paths as actionable blockers before switching machines;
- keep session memory updated after each meaningful task so the next machine can resume without chat history.
