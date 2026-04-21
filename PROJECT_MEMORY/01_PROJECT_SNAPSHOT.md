# Project Snapshot

Project:
- Dekorartstroy CRM and estimate workflow application.

Core purpose:
- manage estimates, projects, counterparties, contract generation, and later finance workflow in one practical desktop tool.

Primary code files:
- `CRM.py` - main CRM shell, project lifecycle, counterparties, documents, finance screens, and entry points into estimate work.
- `smeta.py` - active estimate editor and price list manager.

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
2. Fix bugs found from real use and screenshots.
3. Validate the full estimate -> project -> counterparty -> contract path.
4. After stability, move into the shared cash desk implementation.
5. Keep the future browser-based deployment plan documented, but postpone active web work until the desktop workflow is stronger.

What is already known:
- `smeta.py` is not dead legacy code; it is still a live daily-use tool.
- The biggest portability problem was stale absolute paths, not missing saves.
- Path handling should be relative to the project folder or repairable when older data contains machine-specific paths.
- The current application is a desktop `customtkinter` app with local SQLite and file-based document storage, so browser access will require a web layer or a staged migration rather than a simple hosting switch.

What not to do casually:
- do not refactor all of `CRM.py` just for cleanliness;
- do not rebuild the whole estimate architecture from scratch;
- do not move binary working data into normal git history;
- do not start deep DB migrations without a concrete need.
