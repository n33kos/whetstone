# whetstone

A daily code-and-concept sharpening tool. Each morning generates one focused lesson — a single source file in your primary language with the concept embedded as a structured comment block, a failing test below it, and a clearly-marked area to write the solution. Five to fifteen minutes per day, no stacking, no shaming, no perfectionism trap.

Sibling project to [imprint](https://github.com/n33kos/imprint) (behavioral profile) and [ursula](https://github.com/n33kos/ursula) (voice profile). Whetstone is the **skill-and-knowledge** layer — it keeps you sharp on patterns, architecture, distributed systems, language internals, and the terminology that goes with them, by feeding you one well-shaped lesson every day, growing the curriculum organically based on what you actually engaged with.

## Status

Pre-build. Scaffolding committed locally. Not yet pushed to GitHub.

## Installation (planned)

```
/plugin install n33kos/whetstone
```

(Not yet functional.)

## How it works (planned)

1. **One-time setup** (`/whetstone:bootstrap`) — installs deps into `~/.whetstone/`, runs a ~15-minute conversational self-assessment + goal-statement, seeds your initial knowledge map, installs the launchd plist that fires the daily cron.
2. **Daily at 7am Mountain** — cron analyzes yesterday's file (test pass/fail, your bottom-of-file notes, the diff), updates the knowledge map, picks today's topic from the catalog (mostly reinforcement, occasional exploration of unvisited regions), writes a new single-file lesson at `~/.whetstone/lessons/YYYY-MM-DD/lesson.ts` (or `.rb`, etc.), opens it in VS Code.
3. **You spend 5-15 minutes** reading the lesson comment block, writing code to make the failing tests pass, and optionally jotting thoughts at the bottom of the file that feed tomorrow's planner.
4. **No stacking.** If you skip a day, tomorrow's lesson is fresh. The topic naturally resurfaces sooner via spaced review.
