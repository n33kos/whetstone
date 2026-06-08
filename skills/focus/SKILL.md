---
name: whetstone:focus
description: Edit the user's whetstone `current_focus_areas` list — bias the planner toward specific sections or topics for the next while. The planner heavily weights focus areas but still pulls some exploration picks from outside. Triggers on "/whetstone:focus", "set whetstone focus", "bias whetstone toward <X>", "this week I want to learn <X>", "drop focus on <X>".
---

# whetstone:focus

Edit the `current_focus_areas` list in `~/.whetstone/state.json` to bias the planner's topic selection. Focus areas are catalog section names or specific topic ids — when a topic matches, its planner score is multiplied by ~1.6, dominating most reinforcement picks while still allowing exploration days to escape.

## Step 1 — Resolve what the user wants

The user's request is one of:

- **Add a focus area** ("focus on distributed systems", "this week I want concurrency").
- **Remove a focus area** ("stop biasing toward GoF patterns", "drop distributed systems").
- **Replace the whole list** ("set focus to concurrency and reliability only").
- **Just show the current list** ("what's my focus", "show focus areas").

Save the operation as `op` (one of `add`, `remove`, `replace`, `show`).

## Step 2 — Resolve the values to section ids

Read `~/.whetstone/catalog/topics.yml` and collect the unique `section` values. Save the set as `sections`.

For each value the user named, match against `sections` case-insensitively. If a value is ambiguous (e.g., "patterns" could be `gof-patterns` or `modern-patterns`), ask the user to disambiguate.

If a value looks like a specific topic id (kebab-case, exists in the catalog), accept it as-is — the planner accepts both.

## Step 3 — Apply the edit

Read `~/.whetstone/state.json`. Save the current `current_focus_areas` as `before`.

Apply the operation:

- `add`: union the new values into the existing list (no duplicates).
- `remove`: filter out the named values.
- `replace`: overwrite with exactly the named values.

Write the updated state.json back.

## Step 4 — Confirm

Print the before/after lists side by side. Mention that the change takes effect at the next lesson generation (cron at 7am, or `/whetstone:generate` now).

If the new list is empty, tell the user the planner will fall back to pure reinforcement weighting against the knowledge map.

For the `show` op, just print the current list and skip the edit.
