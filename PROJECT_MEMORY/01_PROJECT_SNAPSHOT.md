# Project Snapshot

Project:
- Dekorartstroy CRM and estimate workflow application.

Core purpose:
- manage estimates, projects, counterparties, contract generation, documents, and later finance workflow in one practical system;
- gradually move the most important daily work from desktop screens into a browser version hosted on the server.

Primary code files:
- `CRM.py` - main CRM shell, project lifecycle, counterparties, documents, finance screens, and desktop entry points into estimate work.
- `smeta.py` - active desktop estimate editor and price list manager.
- `webapp/main.py` - FastAPI web entry points.
- `webapp/db.py` - PostgreSQL-backed browser data access and estimate persistence.
- `webapp/templates/estimate_editor.html` - first editable web estimate screen.
- `webapp/static/estimate_editor.js` - browser-side estimate editor behavior.

Primary data files:
- `dekorart_base.db` - main SQLite database for projects and CRM data.
- `dekorart_prices.db` - price list SQLite database.

Primary template:
- `contract_template_physical.docx`

Business flow:
1. Create estimate.
2. Create project from estimate.
3. Create or attach counterparty.
4. Generate contract.
5. Continue execution through project documents and finance.

Non-negotiable rule:
- work starts from the estimate, not from the counterparty.

Current product priority:
1. Keep the live workflow stable.
2. Continue the browser version so the owner can work and review through the server.
3. Make the web estimate flow truly convenient for daily use.
4. After estimate stability, move project editing, documents, and contract-adjacent screens into the browser.
5. After workflow stability, continue toward the shared cash desk implementation.

What is already known:
- `smeta.py` is still a live working tool, not dead legacy code.
- The biggest portability problem was stale absolute paths, not missing saves.
- The current application started as a desktop `customtkinter` app, so browser access required a real web layer rather than a simple hosting switch.
- A Linux server baseline exists on Ubuntu 24.04 with PostgreSQL, Nginx, UFW, a dedicated `crmadmin` user, uploaded project files, and imported CRM data.
- A browser MVP already exists under `webapp/` and is deployed on the server.
- The browser layer already supports login, project list, project detail, document download, and the first editable estimate screen.
- The web estimate screen already supports section creation, item creation, item editing, row deletion, total recalculation, discount recalculation, and draft save back into PostgreSQL and server storage.
- At the end of the last session, local repo, GitHub, and server were synchronized on commit `e76391b` (`Add browser estimate editor workflow`).

What not to do casually:
- do not refactor all of `CRM.py` just for cleanliness;
- do not rebuild the whole estimate architecture from scratch;
- do not move binary working data into normal git history;
- do not start deep DB migrations without a concrete need;
- do not split the desktop and web logic into a huge architecture rewrite before the browser workflow is stable enough to justify it.
