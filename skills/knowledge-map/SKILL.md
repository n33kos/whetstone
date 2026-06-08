---
name: whetstone:knowledge-map
description: Print the user's current whetstone knowledge map — per-topic confidence scores ordered by recent activity. No dashboard; tabular text output. Triggers on "/whetstone:knowledge-map", "show me my knowledge map", "what does whetstone think I know", "list my topic confidence scores".
---

# whetstone:knowledge-map

Surface the current state of the user's knowledge map as scannable text. No charts, no HTML — terminal output.

## Step 1 — Load the map

Read `~/.whetstone/knowledge-map.yml`. Save the topics dict as `kmap`.

Read `~/.whetstone/catalog/topics.yml`. Save the topics list as `catalog`.

## Step 2 — Render

Print a table with these columns:

| topic id | section | confidence | last seen | next review | engagements |

Order by `last_seen_at` descending (most recent first). Topics with no `last_seen_at` go at the bottom in alphabetical id order.

Confidence formatting: `0.00` to `1.00`, two decimals. Add a visual bar if it fits: `▇▇▇▇▇▇▇▁▁▁` (10-char Unicode block bar scaled from confidence).

After the table, print a one-line summary:

> "Tracking N topics across S sections. Average confidence: X.XX. Topics never seen: M."

## Step 3 — Highlight gaps

If there are entire sections from the catalog where NO topic has been engaged, list them under a "Never-explored sections" header. These are the planner's natural exploration territory.

## Step 4 — Optional: focus-area context

If `~/.whetstone/state.json` has a non-empty `current_focus_areas`, mention which sections are currently being prioritized. Topics in those sections are weighted higher by the planner regardless of confidence.

Keep total output well under one terminal screen. If there are >50 engaged topics, default to showing the most recent 25 and mention "(N more — pass --all to list everything)".
