# Memory Index

Read order for a fresh session:
1. `01_PROJECT_SNAPSHOT.md`
2. `07_NEXT_STEPS.md`
3. `14_HOME_OFFICE_CONTINUITY.md`
4. `06_SESSION_LOG.md`
5. `05_DECISIONS.md`
6. `09_BUGS_AND_RISKS.md`

File map:
- `01_PROJECT_SNAPSHOT.md` - one-file orientation to the project, product, code, and current priorities.
- `02_WORKING_AGREEMENTS.md` - rules of collaboration, scope discipline, and update habits.
- `03_ARCHITECTURE_AND_DATA.md` - code ownership, databases, storage model, and path strategy.
- `04_DOMAIN_RULES.md` - business workflow and behavior rules that must stay consistent.
- `05_DECISIONS.md` - confirmed decisions and why they were made.
- `06_SESSION_LOG.md` - compressed chronological memory of sessions and outcomes.
- `07_NEXT_STEPS.md` - current queue, blockers, and immediate focus.
- `08_BACKLOG.md` - lower-priority work not yet in the active queue.
- `09_BUGS_AND_RISKS.md` - known risks, rough edges, and watch items.
- `10_TESTING_AND_QA.md` - manual test matrix and verification notes.
- `11_ENVIRONMENT_AND_PATHS.md` - machine, repo, server, and storage realities.
- `12_CONVERSATION_RULES.md` - how to preserve chat decisions in project memory.
- `13_WEB_DEPLOYMENT_PLAN.md` - what and why is being built (stages 1-7, deployment strategy).
- `../WEB_SERVER_SETUP.md` - step-by-step deployment walkthrough from scratch (tactics, the only document with a full deployment walkthrough).
- `14_HOME_OFFICE_CONTINUITY.md` - startup and handoff rules for switching between office and home work.

Deployment docs — division of roles:
- `13_WEB_DEPLOYMENT_PLAN.md` — what and why is being built (stages 1-7, deployment strategy).
- `../WEB_SERVER_SETUP.md` — step-by-step deployment walkthrough from scratch (tactics; the only document with a full deployment walkthrough). These two are complementary, not duplicates.

Quick rule:
- if something must still matter next week, it should live in one of these files.

Current anchor:
- browser MVP is deployed on the server;
- browser estimate editor is implemented and saved in git commit `222230e` on branch `hermes/integrate-origin-master-20260423`;
- local repo, GitHub, and server are aligned on the current session.
