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
