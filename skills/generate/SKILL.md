---
name: whetstone:generate
description: Force-generate a new whetstone lesson now, bypassing the daily cron. Useful for "I have free time, give me another one." Multiple lessons per day are allowed but the planner notes that signal. Triggers on "/whetstone:generate", "give me another lesson", "generate a new whetstone lesson", "force generate today's lesson", "whetstone me something on <topic>".
---

# whetstone:generate

Force-generate a new lesson, overwriting today's if one already exists. Use sparingly — the daily cadence is the point. But sometimes you have an extra 15 minutes.

## Step 1 — Resolve any user-supplied hint

If the user supplied a topic hint in their request (e.g., "generate a lesson on circuit breakers"), save it as `topic_hint`. Otherwise leave it unset.

If the user supplied a language hint ("in Ruby", "use TypeScript"), save it as `language_hint`. Otherwise leave it unset.

## Step 2 — Invoke the generator

Build the command:

```
~/whetstone/scripts/generate-lesson.sh --force
  [--topic "$topic_hint"]
  [--language "$language_hint"]
```

Include the `--topic` flag only if `topic_hint` is set. Same for `--language`.

Run it and save the result as `generation_log`.

## Step 3 — Report

Print the lesson path, the chosen topic, the chosen language, and the mode (reinforcement / exploration / override). The script's stdout already includes these — surface them to the user verbatim.

## Caveat to mention

If the user is forcing more than two lessons in a single day, gently mention that the daily cadence is intentional — sharpening compounds because it's small and consistent, not because it's big. They can override; that's just a one-line nudge.
