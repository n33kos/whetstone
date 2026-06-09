# Lesson shape — spec for the generator's Claude prompt

Each lesson is a **directory** under `~/.whetstone/lessons/YYYY-MM-DD/`, not a
single file. The generator emits whatever set of files actually teaches the
concept; rigid templates are gone.

Every lesson directory must contain at minimum:

- `README.md` — concept body, why-it-matters, real-world examples,
  references. This is the lesson's prose layer.
- `scratch.md` — empty file for the user's notes. Parsed by tomorrow's
  planner. Supports a `NEXT: <topic-id-or-keywords>` directive on its
  own line to override the next day's pick.
- A **test file** — the failing test the user makes pass. Vitest's default
  include picks up `*.test.ts`; RSpec picks up `*_spec.rb`. Name accordingly.
- One or more **scaffold files** — the code the user fills in. The test
  imports symbols these files declare. Scaffolds must parse/compile but
  the test must fail until the user implements.
- `lesson.json` — written by the planner, not the model. Contains topic_id,
  title, section, mode, language, generated_at, run_command, scaffold_files.

The generator may emit any additional files the concept demands —
multi-process setups can have separate `app.ts` and `sidecar.ts` files,
distributed-systems lessons might include a `protocol-trace.txt` and a
quiz, etc. There is no upper file count.

## Manifest format (model output)

The generator asks Claude to emit a single response in this block format:

```
=== RUN_COMMAND ===
<the shell command that runs the test>
=== SCAFFOLD_FILES ===
<one filename per line — the files the user is supposed to edit>
=== FILE: <filename> ===
<file contents verbatim>
=== FILE: <filename> ===
<file contents verbatim>
...
=== END ===
```

The planner parses this, writes each file, and synthesizes `lesson.json`
from its own inputs (topic_id, mode, etc.) plus the manifest's
RUN_COMMAND and SCAFFOLD_FILES sections.

## Why this shape

A sidecar pattern lesson with a single in-process function and a single
file teaches the *retry algorithm*, not the *process boundary*. A real
sidecar lesson needs two files plus a test that spawns both as separate
processes communicating over localhost. CQRS lessons need separate
command and query files. Distributed-systems lessons may not be runnable
code at all — they may be a trace to read and questions to answer.

The unifying constraint isn't "one file" — it's "the failing test
forces engagement with the concept, and the file structure mirrors how
the concept manifests in real systems."
