---
name: whetstone:today
description: Open today's whetstone lesson in VS Code. If today's lesson doesn't exist yet (cron hasn't fired, or user is invoking before 7am), generate it synchronously first. Triggers on "/whetstone:today", "open today's lesson", "show me today's whetstone", "what's today's lesson".
---

# whetstone:today

Surface today's lesson — generate it on demand if the cron hasn't fired yet, otherwise just open the existing file in VS Code.

## Step 1 — Check whether today's lesson exists

Run `ls ~/.whetstone/lessons/$(date +%Y-%m-%d)/lesson.* 2>/dev/null` and save the result as `existing_lesson`.

## Step 2 — Generate if missing, otherwise open

If `existing_lesson` is empty, run `~/whetstone/scripts/generate-lesson.sh` and save the result as `generation_log`. The script picks the topic, writes the lesson, and opens it in VS Code automatically.

If `existing_lesson` is non-empty, run `code $existing_lesson` to open it. VS Code will join the existing window if one is open.

## Step 3 — Report

Print the lesson path and the topic id (parsed from the file's header) so the user has it in scrollback for reference later.
