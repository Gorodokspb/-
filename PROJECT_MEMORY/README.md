# PROJECT_MEMORY

This folder is the persistent project memory for long-running work with Codex.

Goal:
- keep business context, technical decisions, recent progress, and next steps outside chat history;
- let a new session resume quickly without re-explaining the project;
- separate stable knowledge from temporary notes.

How to use:
- `00_INDEX.md` tells where everything lives.
- `01_PROJECT_SNAPSHOT.md` is the best high-level orientation file.
- `06_SESSION_LOG.md` stores condensed session history.
- `07_NEXT_STEPS.md` stores the immediate execution queue.
- `05_DECISIONS.md` stores choices that should survive across sessions.

Update policy:
- after major coding work: update session log and next steps;
- after confirmed product or technical choice: update decisions;
- after discovering a workflow pain, regression, or uncertainty: update bugs and risks;
- after manual verification: update testing notes.

Memory design principle:
- stable facts go into thematic files;
- short-lived progress goes into session log;
- active priorities go into next steps;
- unresolved items stay visible instead of being silently forgotten.
