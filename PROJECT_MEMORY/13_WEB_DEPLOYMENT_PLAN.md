# Web Deployment Plan

Current status:
- browser MVP is already deployed on the server;
- login, project list, project detail, and document download are live;
- the first editable browser estimate screen is also implemented and deployed;
- the latest synchronized web milestone is git commit `e76391b` (`Add browser estimate editor workflow`).

Goal:
- move from the current single-user desktop workflow to a server-hosted system that the owner can use and a colleague can test through a browser with login and password.

Important reality:
- the current app started as a desktop `customtkinter` program;
- browser access requires a real web-facing application layer;
- remote desktop is not an accepted fallback for this project.

## Recommended Direction

Target model:
- keep the current desktop app as the live fallback tool for now;
- continue building the web version in stages on the server;
- host the web version and central database on the rented server;
- give the colleague a limited tester account with login/password access.

Why this is the right path:
- no local installation is needed for the tester;
- feedback can happen against one central version;
- access control is cleaner than sharing a desktop session;
- this is a real foundation for future multi-user work.

## Architecture Choice

Working stack now:
- backend: `FastAPI`;
- frontend: server-rendered templates plus page-specific JavaScript;
- database: PostgreSQL on the server;
- files: managed server storage for estimates, contracts, and uploads;
- auth: session-based login/password.

## Suggested Migration Stages

Stage 1. Stabilize the desktop source of truth
- finish manual verification of the current CRM workflow;
- keep fixing real bugs in `CRM.py` and `smeta.py`;
- preserve office/home continuity.

Stage 2. Browser MVP
- login page;
- project list;
- project card summary;
- linked documents view;
- read-only or limited tester mode.

Status:
- completed.

Stage 3. First active browser editing
- estimate header editing;
- estimate sections and positions;
- draft save/load against PostgreSQL and server storage.

Status:
- first version completed in `e76391b`.

Stage 4. Improve browser estimate workflow
- better row editing UX;
- cleaner table behavior;
- clearer save feedback;
- estimate PDF flow;
- tighter connection between estimate, project, and documents.

Status:
- active next stage.

Stage 5. Move more project operations into the browser
- create/edit projects;
- attach counterparties;
- edit statuses;
- add notes and project events.

Stage 6. Move contract-adjacent workflows
- contract settings;
- document-generation handoff;
- server-friendly replacement for Windows-only Word COM generation.

Stage 7. Switch routine testing to the browser version
- let the colleague test only the browser version;
- keep desktop CRM as backup until the browser flow is reliable.

## Immediate practical focus

Most valuable next slices:
1. polish the web estimate UX;
2. add web estimate PDF export or its server-side generation flow;
3. expose more project editing directly in the browser;
4. continue reducing dependence on local desktop-only actions.

## Risks To Watch

Main risks:
- trying to port every desktop detail before the browser workflow is stable;
- mixing temporary manual server uploads with git history for too long;
- leaving project memory behind the real deployed state;
- relying on Windows-only document generation too deep into the server/web transition.
