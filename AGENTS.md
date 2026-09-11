# Agent Instructions

This project uses a coordination file system in `project-context/`.
These files give you persistent memory across sessions. **Read them before starting any work.**

## Starting a Session

Read these files in order:
1. `project-context/PROJECT_CONTEXT.md` — current project state, phase, team
2. `project-context/GLOSSARY.md` — terminology (use these terms exactly)
3. `project-context/HANDOFF.md` — what happened last session, what to do next

Also read when relevant:
- `project-context/STRUCTURE.md` — before creating or moving files
- `project-context/WAYSOFWORKING.md` — for workflows, failure patterns, verification steps
- `project-context/PROVENANCE.md` — to understand why a decision was made
- `project-context/EXPERIMENT_JOURNAL.md` — to see what was tried and learned

## Ending a Session

Update `project-context/HANDOFF.md` with:
- What you accomplished (specific files, decisions, results)
- What's blocked or unresolved
- What the next session should start with
- Non-obvious context the next agent needs

## Continuous Improvement

| When you... | Update |
|-------------|--------|
| Use a term not in the glossary | `project-context/GLOSSARY.md` |
| Make a design or architecture decision | `project-context/PROVENANCE.md` |
| Hit an error and find the fix | `project-context/WAYSOFWORKING.md` |
| Create or move files | `project-context/STRUCTURE.md` |
| Run an experiment or benchmark | `project-context/EXPERIMENT_JOURNAL.md` |
| Change the project phase or milestone | `project-context/PROJECT_CONTEXT.md` |
| Finish any session | `project-context/HANDOFF.md` |
