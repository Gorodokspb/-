# Web Deployment Plan

Goal:
- move from the current single-user desktop workflow to a server-hosted system that the owner can use and a colleague can test through a browser with login and password.

Important reality:
- the current app is a desktop `customtkinter` program;
- moving it to a rented server does not by itself create a browser application;
- browser access requires a web-facing application layer.
- remote desktop is not an accepted fallback for this project.

## Recommended Direction

Target model:
- keep the current desktop app as the live working tool for now;
- build a staged web version for browser access;
- host the web version and central database on a rented server;
- give the colleague a limited tester account with login/password access.

Why this is the right path:
- no local installation is needed for the tester;
- feedback can happen against one central version;
- access control becomes cleaner than sharing a desktop session;
- this is a real foundation for future multi-user work.

## Architecture Choice

Recommended stack for the future web version:
- backend: Python web framework such as `FastAPI`;
- frontend: server-rendered templates first, or a lightweight SPA only if needed later;
- database: PostgreSQL on the server;
- files: managed uploads/storage for contracts, estimates, and attached documents;
- auth: login/password with role separation.

Roles:
- owner/admin: full access;
- tester: login allowed, limited editing or read-only access depending on the screen.

Why not keep SQLite for the shared server version:
- SQLite is good for the current desktop tool but is a weak base for concurrent browser access;
- a central server with more than one human touching the system should use a server database.

## Hosting Guidance

If the goal is true browser access:
- prefer a Linux VPS/VDS because it is cheaper and more natural for web deployment.

Rejected approach:
- do not use Linux or Windows remote desktop as the testing model;
- the colleague must access the system through a browser.

## Suggested Migration Stages

Stage 1. Stabilize the desktop source of truth
- finish manual verification of the current CRM workflow;
- keep fixing real bugs in `CRM.py` and `smeta.py`;
- confirm path portability between home and office later in live testing.

Stage 2. Extract the domain model
- document the tables, entities, and workflow rules that the web version must preserve;
- identify reusable business logic now embedded directly in UI handlers;
- separate data rules from `customtkinter` screen code where practical.

Stage 3. Build browser MVP
- login page;
- project list;
- project card summary;
- counterparties read view;
- document list;
- read-only or limited tester mode.

Stage 4. Add active editing
- create/edit projects;
- attach counterparties;
- edit statuses;
- add notes and project events.

Stage 5. Move estimate and contract workflows
- estimate header and rows;
- draft save/load;
- contract settings and generation flow;
- document storage integration.

Stage 6. Switch daily testing to the browser version
- let the colleague test only the browser version;
- keep desktop CRM as backup until the browser flow is reliable.

## First Browser MVP Scope

Minimum useful scope:
- authentication;
- list of projects;
- project detail page;
- visible statuses and core dates;
- linked counterparty summary;
- linked documents list;
- tester account with limited rights.

Not in the first MVP unless urgently needed:
- full estimate editor;
- full finance module;
- document generation in all variants;
- advanced admin settings.

## Risks To Watch

Main risks:
- trying to "host" the desktop app and calling it a web solution;
- carrying UI logic directly into backend code without extracting business rules;
- reusing SQLite too long for shared browser access;
- mixing production and testing data without roles or environment separation.

## Practical Next Decision

Confirmed answer:
- build a real browser MVP on a rented server;
- keep the current desktop app only as the temporary internal working baseline during transition.
