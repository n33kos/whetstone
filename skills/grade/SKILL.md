---
name: whetstone:grade
description: Grade the user's whetstone lesson implementation and write the critique into the lesson's scratch.md so tomorrow's planner picks it up. Triggers on "/whetstone:grade", "grade me on this", "grade my lesson", "review my whetstone implementation", "quick grade and toss it in the scratchpad".
---

# whetstone:grade

Grade a completed (or abandoned) lesson implementation, deliver the critique conversationally, and persist the takeaways into the lesson's scratchpad so the spaced-review planner can act on them.

## Step 1 — Locate the lesson

ALWAYS resolve the current date from the system, never from memory or conversation context — the model's notion of "today" drifts and is not trustworthy. Run `date +%Y-%m-%d` and save the result as `today`.

Target the latest exercise possible. Run `ls -d ~/.whetstone/lessons/$today 2>/dev/null` and save the result as `lesson_dir`.

If `lesson_dir` is empty (today's lesson has not been generated yet), fall back to the newest lesson directory that exists: run `ls -d ~/.whetstone/lessons/*/ | sort | tail -1` and save that as `lesson_dir`.

If the user named a specific date, use that date's directory instead and set `lesson_dir` accordingly.

## Step 2 — Read the work

Read `lesson_dir/lesson.json` and save the `scaffold_files` list as `scaffold_files`.

Read every file in `scaffold_files`, plus `lesson_dir/README.md` for the concept context. The scaffolds are the user's work product; the README defines what the lesson intended to teach.

Run the lesson's test via the `run_command` from `lesson_dir/lesson.json` and save the result as `test_result`.

## Step 3 — Grade

Assess the implementation as a staff engineer reviewing a learning exercise — honest, specific, blame-free. Cover:

- **Letter grade** (A through F, plus/minus allowed) with a one-sentence justification anchored to `test_result` and the concept.
- **What's idiomatically right** — name the things the user got correct, especially where they match how the concept manifests in real production systems.
- **Self-critiques confirmed or corrected** — if the user named their own concerns, address each one directly: confirm, sharpen, or push back.
- **What they missed** — issues the user didn't name, ordered by real-world severity, not pedantry. Distinguish "fix this to actually learn the concept" from "good to know" nits.
- **The A path** — one sentence: what specific changes would raise the grade.

Deliver the full critique conversationally first.

## Step 4 — Persist to the scratchpad

Append a `## Critique to address (from grading)` section to `lesson_dir/scratch.md` containing the grade, the concept takeaways worth retaining, and the missed-issue list in terse bullet form. Preserve any notes the user already wrote — append, never overwrite.

The scratchpad is parsed by tomorrow's planner, so the persisted critique becomes spaced-review signal automatically.

## Step 5 — Offer the follow-up hook

If the grade is below A, mention the user can write `NEXT: <topic-id>` in the scratchpad to revisit this topic tomorrow, or just let spaced review resurface it naturally. Don't push — no stacking, no shaming.
