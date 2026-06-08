# whetstone

A daily code-and-concept sharpening tool. Each morning generates one focused lesson — a single source file in your primary language with the concept embedded as a structured comment block, a failing test below it, and a clearly-marked area to write the solution. Five to fifteen minutes per day. No stacking, no shaming, no perfectionism trap.

Sibling project to [imprint](https://github.com/n33kos/imprint) (behavioral profile) and [ursula](https://github.com/n33kos/ursula) (voice profile). Whetstone is the **skill-and-knowledge** layer — it keeps you sharp on patterns, architecture, distributed systems, language internals, and the terminology that goes with them, by feeding you one well-shaped lesson every day, growing the curriculum organically based on what you actually engaged with.

## Status

v0.0.1 — local-only. Not yet on the plugin marketplace. The repo runs on the author's machine; share at your own risk.

## How it works

1. **One-time setup** (`/whetstone:bootstrap`) — installs Vitest + RSpec into `~/.whetstone/`, runs a ~15-minute conversational self-assessment, seeds the initial knowledge map, installs the launchd plist that fires the daily cron.
2. **Daily at 7am local time** — cron reads yesterday's lesson (test pass/fail, your scratchpad notes, what you wrote in the "your code here" zone), updates `~/.whetstone/knowledge-map.yml`, picks today's topic from the catalog (mostly reinforcement-weighted against your weak spots, every ~7th day a forced exploration), writes a new single-file lesson at `~/.whetstone/lessons/YYYY-MM-DD/lesson.{ts,rb}`, opens it in VS Code.
3. **You spend 5-15 minutes** reading the concept block, writing code to make the failing test pass, and optionally jotting thoughts at the bottom of the file. Anything you write there feeds tomorrow's planner — including a `NEXT: <topic-id-or-keywords>` directive on its own line to force tomorrow's topic.
4. **No stacking.** If you skip a day, tomorrow's lesson is fresh. The topic naturally resurfaces sooner via spaced review.

## Skills

| Skill | What it does |
|---|---|
| `/whetstone:bootstrap` | One-time setup. Self-assessment, dep install, launchd plist. Idempotent. |
| `/whetstone:today` | Open today's lesson in VS Code (generate it if the cron hasn't fired yet). |
| `/whetstone:generate` | Force-generate a new lesson now, bypassing the cron. |
| `/whetstone:reseed-catalog` | Reset the catalog. Default or custom. |
| `/whetstone:knowledge-map` | Print the current knowledge map as text. |
| `/whetstone:focus` | Edit the `current_focus_areas` list to bias the planner. |

## File layout

```
~/whetstone/                     # this repo
├── .claude-plugin/plugin.json   # plugin manifest
├── catalog/
│   ├── topics.yml               # ~120 topics, 13 sections
│   └── sources.yml              # citation library (books, papers, RFCs)
├── skills/                      # the six skills above
├── scripts/
│   ├── install.sh               # one-time setup
│   ├── uninstall.sh             # clean removal
│   ├── generate-lesson.sh       # cron entry point
│   └── plan_and_generate.py     # the planner brain
├── templates/
│   ├── lesson-typescript.ts     # TS lesson template
│   ├── lesson-ruby.rb           # Ruby lesson template
│   └── launchd.plist            # cron template
└── docs/
    └── catalog-shape.md         # how to author / extend the catalog

~/.whetstone/                    # user state (created by install.sh)
├── package.json, node_modules/  # shared Vitest install
├── Gemfile, Gemfile.lock        # shared RSpec install
├── catalog/                     # local copy of the catalog (edit freely)
├── knowledge-map.yml            # per-topic confidence + scheduling
├── state.json                   # current_language, focus_areas, goals
└── lessons/YYYY-MM-DD/lesson.ts
```

The split is intentional. The repo is the seed; `~/.whetstone/` is the per-user state that grows over time and stays on this machine.

## Installation

```
~/whetstone/scripts/install.sh
```

Then in Claude Code: `/whetstone:bootstrap`.

## Catalog

The default catalog covers language fundamentals, data structures, OO design, all 23 GoF patterns, modern patterns (DI, repository, saga, outbox, idempotency, hexagonal, CQRS, event sourcing, sidecar, ambassador, strangler fig), architectural styles, distributed systems (CAP/PACELC, Paxos, Raft, consistent hashing, vector clocks, LSM trees, append-only logs), concurrency primitives, storage internals, networking, testing patterns, observability (RED, USE, SLOs), reliability (circuit breakers, bulkheads, retries, rate limiting, canary deploys), and security primitives (OAuth, JWT, CSRF, XSS, STRIDE).

See `docs/catalog-shape.md` to author new topics or swap in a custom catalog for non-code learning.

## Languages

TypeScript is primary, Ruby cycles in every 5th day by default. Both are configurable in `~/.whetstone/state.json`. Other languages can be added by writing a new template under `templates/` and extending the planner — out of scope for v1.

## Uninstall

```
~/whetstone/scripts/uninstall.sh
```

Removes the launchd plist and (with confirmation) `~/.whetstone/`. Does not touch the repo itself.
