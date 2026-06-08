---
name: whetstone:bootstrap
description: One-time whetstone setup. Walks the user through a ~15-minute conversational self-assessment, captures stated goals, seeds the knowledge map, installs shared dev deps (Vitest, RSpec), and installs the launchd plist that fires the daily 7am lesson generator. Idempotent. Triggers on "/whetstone:bootstrap", "set up whetstone", "initialize whetstone", "first-time whetstone setup".
---

# whetstone:bootstrap

One-time setup for whetstone — the daily code-and-concept sharpening plugin.

## Step 1 — Run the install script

Run `~/whetstone/scripts/install.sh` and save the result as `install_log`.

The script is idempotent. It creates `~/.whetstone/` if missing, installs shared dev deps (Vitest, RSpec) into that directory, seeds the catalog by copying from `~/whetstone/catalog/`, scaffolds `knowledge-map.yml` and `state.json` if absent, and installs the launchd plist at `~/Library/LaunchAgents/com.whetstone.daily.plist`.

If `install_log` reports a missing dependency (node, npm, bundler), pause and tell the user how to install it before continuing.

## Step 2 — Conversational self-assessment

The catalog at `~/.whetstone/catalog/topics.yml` is organized into top-level **sections**. Read it and save the section list as `sections`.

For each section in `sections`, ask the user a single high-level question about their comfort level. Frame it as a conversation, not a survey. Example:

> "How comfortable are you with **distributed systems** — things like CAP, consensus algorithms (Paxos, Raft), consistent hashing, vector clocks, append-only logs? On a rough 0-to-5 scale where 0 means 'haven't touched it' and 5 means 'I could teach this'."

Some sections deserve a follow-up:

- If the user rates **language fundamentals** as 4+, ask which specific language features they've gone deep on (type systems, async, memory, closures).
- If they rate **GoF patterns** as 2 or below, ask which patterns they've actually applied recently — even one or two.
- If they rate **distributed systems** or **storage** as 4+, ask if there's a specific paper or system they've implemented or operated.

Don't grill them. Aim for ~10-15 minutes total. The goal is a rough confidence map, not a precise audit.

## Step 3 — Capture goals

Ask:

> "What do you want whetstone to bias toward for the next month or two? Could be a section ('I want to get strong on concurrency'), a project context ('I'm about to design an event-driven pipeline'), or a feeling ('I've been writing too much glue code, I want to think harder')."

Save the response as `stated_goals`.

## Step 4 — Identify exploration territory

Compare the sections the user mentioned naturally during steps 2 and 3 against the full `sections` list. Save the unmentioned sections as `exploration_territory`. These will surface preferentially during exploration days.

## Step 5 — Write the state files

Translate the conversation into `~/.whetstone/knowledge-map.yml` and `~/.whetstone/state.json`:

- **knowledge-map.yml** — for each topic in a section the user gave a confidence score for, set `confidence` to `(section_score / 5.0)` and leave `last_seen_at` / `next_review_at` null. Topics the user gave specific follow-up depth on get a slightly higher (`+0.1`) confidence. Topics in sections the user didn't mention at all stay absent from the map — the planner treats absent topics as exploration territory.
- **state.json** — set `current_focus_areas` from the user's stated goals (use section names from the catalog where possible). Set `goals` to a list of the user's stated-goal sentences. Set `bootstrap_completed_at` to today's ISO date.

Use `~/.claude/skills/notion-markdown/`-style YAML/JSON care here — don't break the schemas. Read the existing files first, edit in place, preserve any keys you don't recognize.

## Step 6 — Confirm and offer first lesson

Summarize back to the user in 2-3 sentences: top three weak areas, top three strong areas, and the stated focus.

Then ask: "Want to generate your first lesson right now, or wait for tomorrow's 7am cron?"

If yes, run `~/whetstone/scripts/generate-lesson.sh` and report the path it wrote.

## Re-running

If the user invokes `/whetstone:bootstrap` again later, treat it as a re-assessment — re-run the install script (idempotent), re-ask the section questions (their confidence may have grown), and merge the new scores into the existing knowledge map rather than overwriting.
