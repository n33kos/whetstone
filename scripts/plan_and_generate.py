#!/usr/bin/env python3
"""
Whetstone planner + generator.

Picks today's topic, prompts Claude to emit a lesson directory (whatever set
of files actually teaches the concept), writes everything to
~/.whetstone/lessons/YYYY-MM-DD/, and opens the directory in VS Code.

Lessons are directories, not single files. See templates/lesson-shape.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write(
        "pyyaml is required. Install with: python3 -m pip install --user pyyaml\n"
    )
    sys.exit(2)


REPO    = Path(os.environ.get("WHETSTONE_REPO",  Path.home() / "whetstone"))
STATE   = Path(os.environ.get("WHETSTONE_STATE", Path.home() / ".whetstone"))
LESSONS = STATE / "lessons"


# ──────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class Topic:
    id: str
    title: str
    section: str
    summary: str
    prereqs: list[str]
    related: list[str]
    sources: list[str]
    languages: list[str]
    tags: list[str]


def load_catalog() -> dict[str, Topic]:
    raw = yaml.safe_load((STATE / "catalog" / "topics.yml").read_text())
    out: dict[str, Topic] = {}
    for t in raw.get("topics", []):
        out[t["id"]] = Topic(
            id=t["id"],
            title=t["title"],
            section=t["section"],
            summary=t["summary"],
            prereqs=t.get("prereqs", []) or [],
            related=t.get("related", []) or [],
            sources=t.get("sources", []) or [],
            languages=t.get("languages", ["any"]) or ["any"],
            tags=t.get("tags", []) or [],
        )
    return out


def load_sources() -> dict[str, dict]:
    raw = yaml.safe_load((STATE / "catalog" / "sources.yml").read_text())
    return {s["id"]: s for s in raw.get("sources", [])}


def load_kmap() -> dict[str, Any]:
    return yaml.safe_load((STATE / "knowledge-map.yml").read_text()) or {"topics": {}}


def save_kmap(kmap: dict[str, Any]) -> None:
    (STATE / "knowledge-map.yml").write_text(yaml.safe_dump(kmap, sort_keys=False))


def load_state() -> dict[str, Any]:
    return json.loads((STATE / "state.json").read_text())


# ──────────────────────────────────────────────────────────────────────────
# Yesterday's signal
# ──────────────────────────────────────────────────────────────────────────

def yesterday_dir(today: dt.date) -> Path | None:
    """Find the most recent lesson dir strictly before `today`."""
    if not LESSONS.exists():
        return None
    candidates = sorted(
        (p for p in LESSONS.iterdir()
         if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)),
        reverse=True,
    )
    for c in candidates:
        try:
            d = dt.date.fromisoformat(c.name)
        except ValueError:
            continue
        if d < today:
            return c
    return None


def load_lesson_meta(lesson_dir: Path) -> dict | None:
    """Read lesson.json from a lesson dir."""
    meta_path = lesson_dir / "lesson.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return None


SCRATCH_NEXT_RE = re.compile(r"^\s*NEXT:\s*(.+?)\s*$", re.MULTILINE)


def parse_scratchpad(lesson_dir: Path) -> dict[str, Any]:
    """Read scratch.md and pull any NEXT: directive."""
    scratch = lesson_dir / "scratch.md"
    if not scratch.exists():
        return {"text": "", "next": None}
    text = scratch.read_text(errors="replace")
    nxt = SCRATCH_NEXT_RE.search(text)
    return {"text": text.strip(), "next": (nxt.group(1).strip() if nxt else None)}


def run_test(lesson_dir: Path, meta: dict, timeout: int = 60) -> bool | None:
    """Run the test for a lesson using its declared run_command. None == couldn't run."""
    cmd = meta.get("run_command", "").strip()
    if not cmd:
        return None
    try:
        r = subprocess.run(
            ["bash", "-lc", cmd],
            cwd=STATE, capture_output=True, timeout=timeout, text=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    return r.returncode == 0


def scaffolds_were_edited(lesson_dir: Path, meta: dict) -> bool:
    """Mtime heuristic: any scaffold file modified > 60s after generation."""
    try:
        generated = dt.datetime.fromisoformat(meta.get("generated_at_iso", ""))
    except Exception:
        return False
    cutoff = generated.timestamp() + 60  # grace for write latency
    for fname in meta.get("scaffold_files", []) or []:
        f = lesson_dir / fname
        if f.exists() and f.stat().st_mtime > cutoff:
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────
# Knowledge map update
# ──────────────────────────────────────────────────────────────────────────

def update_kmap_for_yesterday(kmap: dict, today: dt.date) -> dict[str, Any] | None:
    ydir = yesterday_dir(today)
    if ydir is None:
        return None
    meta = load_lesson_meta(ydir)
    if not meta:
        return None
    tid = meta.get("topic_id")
    if not tid:
        return None

    engaged = scaffolds_were_edited(ydir, meta)
    result  = run_test(ydir, meta) if engaged else None
    scratch = parse_scratchpad(ydir)

    topics = kmap.setdefault("topics", {})
    entry = topics.setdefault(tid, {
        "confidence": 0.0,
        "last_seen_at": None,
        "next_review_at": None,
        "engagements": 0,
        "completions": 0,
    })
    entry["last_seen_at"] = ydir.name

    if engaged:
        entry["engagements"] = entry.get("engagements", 0) + 1
        if result is True:
            entry["completions"] = entry.get("completions", 0) + 1
            entry["confidence"]  = min(1.0, entry.get("confidence", 0.0) + 0.25)
            gap = min(60, 2 ** entry["completions"])
        else:
            entry["confidence"]  = min(1.0, entry.get("confidence", 0.0) + 0.10)
            gap = 3
        next_review = dt.date.fromisoformat(ydir.name) + dt.timedelta(days=gap)
        entry["next_review_at"] = next_review.isoformat()

    return {
        "topic_id": tid,
        "engaged": engaged,
        "test_passed": result,
        "scratch_next": scratch["next"],
        "scratch_text": scratch["text"],
    }


# ──────────────────────────────────────────────────────────────────────────
# Topic + language selection (unchanged)
# ──────────────────────────────────────────────────────────────────────────

def pick_topic(catalog, kmap, state, language, today, override_hint, rng):
    topics = kmap.get("topics", {})
    eligible = [t for t in catalog.values() if language in t.languages or "any" in t.languages]
    if not eligible:
        eligible = list(catalog.values())

    if override_hint:
        match = resolve_hint(override_hint, eligible)
        if match:
            return match, "override"

    cadence = int(state.get("exploration_cadence_days", 7))
    if cadence > 0 and (today.toordinal() % cadence == 0):
        unseen = [t for t in eligible if t.id not in topics]
        if unseen:
            return rng.choice(unseen), "exploration"

    focus = set(state.get("current_focus_areas", []) or [])

    def score(t: Topic) -> float:
        entry = topics.get(t.id)
        if entry is None:
            base = 0.55
        else:
            conf = float(entry.get("confidence", 0.0))
            last = entry.get("last_seen_at")
            if last:
                try:
                    days = (today - dt.date.fromisoformat(last)).days
                except ValueError:
                    days = 0
                forget = min(1.0, days / 30.0)
            else:
                forget = 1.0
            base = (1.0 - conf) * 0.7 + forget * 0.3
        if focus and (t.section in focus or t.id in focus):
            base *= 1.6
        return base

    weights = [(score(t), t) for t in eligible]
    weights.sort(key=lambda w: w[0], reverse=True)
    top = weights[:12]
    chosen = rng.choices([t for _, t in top], weights=[s for s, _ in top], k=1)[0]
    return chosen, "reinforcement"


def resolve_hint(hint, pool):
    if not hint:
        return None
    by_id = {t.id: t for t in pool}
    if hint in by_id:
        return by_id[hint]
    needle = hint.lower()
    for t in pool:
        if needle in t.id.lower() or needle in t.title.lower() or needle in t.section.lower():
            return t
    return None


def pick_language(state, today):
    primary = state.get("current_language", "typescript")
    secondary = state.get("secondary_language", "ruby")
    cadence = int(state.get("ruby_cadence_days", 0))
    if cadence > 0 and (today.toordinal() % cadence == 0):
        return secondary
    return primary


# ──────────────────────────────────────────────────────────────────────────
# Lesson generation — multi-file manifest format
# ──────────────────────────────────────────────────────────────────────────

def build_prompt(topic, sources, language, mode, lesson_dir, yesterday_note):
    src_lines = []
    for sid in topic.sources:
        s = sources.get(sid)
        if not s:
            continue
        author = ", ".join(s.get("authors", [])) if s.get("authors") else ""
        year   = s.get("year", "")
        url    = s.get("url", "")
        bits = [b for b in (author, str(year) if year else "", s.get("title", ""), url) if b]
        src_lines.append(" — ".join(bits))
    sources_block = "\n".join(f"  - {line}" for line in src_lines) or "  - (no citations seeded; add canonical ones)"

    yesterday_block = (
        f"\nYesterday's scratchpad note from the learner:\n  \"{yesterday_note}\"\n"
        f"Where appropriate, reference what they wrote in the concept body."
    ) if yesterday_note else ""

    return f"""You are generating today's whetstone lesson — a multi-file lesson directory that actually teaches the concept by making the file structure mirror how the concept manifests in real systems.

Topic to teach:
  id:       {topic.id}
  title:    {topic.title}
  section:  {topic.section}
  summary:  {topic.summary}
  mode:     {mode}
  language: {language}
  tags:     {", ".join(topic.tags) or "(none)"}

Canonical references for this topic:
{sources_block}
{yesterday_block}

The lesson is a directory at {lesson_dir}. You decide what files belong in it.

HARD REQUIREMENTS:

1. The directory must contain a `README.md` with sections: Concept, Why it matters, Where it shows up in real systems, References, How to run this lesson, What you're implementing. Be precise and concrete. Name real production systems. Wrap at column 80.

2. The directory must contain a failing test file. For TypeScript use vitest (`*.test.ts`); for Ruby use rspec (`*_spec.rb`). The test must be runnable as-is and must fail until the learner implements the scaffold(s).

3. The directory must contain one or more scaffold files — the code the learner fills in. Scaffolds must parse/compile (so the test failure is a runtime / assertion failure, not a syntax error).

4. The directory must contain `scratch.md` with a single line `# Scratchpad — for your notes` and four blank lines below it. Tomorrow's planner reads this for `NEXT: <topic>` directives.

5. **Critically**: the file structure must mirror how the concept manifests in real systems. Do not collapse multi-process patterns into a single-file function. For sidecar / hexagonal / CQRS / event-sourcing / saga / actor-model / leader-election / replication / consistent-hashing / gossip and similar topics, give the learner separate files with clear process / module boundaries (e.g., `app.ts` + `sidecar.ts` + `lesson.test.ts` that spawns both as child processes and asserts the cross-process behavior). For purely algorithmic topics (closures, type variance, dynamic programming), a single scaffold file plus a test is fine.

6. If the lesson requires running multiple processes, the test file must orchestrate that itself — start any servers, set timeouts, tear down cleanly. The learner should be able to run a single command and see real cross-process behavior. Debuggability is non-negotiable: tee every child process's stdout AND stderr to the terminal with a `[label]` prefix (write the tee to process.stderr — vitest's interactive reporter redraws the screen and erases raw stdout writes), print a loud red banner when a child crashes or exits nonzero, and make readiness-wait failures say WHICH process failed and point at the captured error output. A learner adding console.log to a scaffold must always see it.

7. The lesson directory MUST contain an executable shell script literally named `run` (no extension). That script is the user-facing entry point — they type `./run` from inside the lesson dir and the tests execute. The script must `cd` into `$HOME/.whetstone` first (so node_modules / Gemfile resolution works) and then invoke vitest / rspec on the absolute path of the test file. For vitest, pass `--reporter=basic` so the linear output preserves teed child-process logs. The run command in the manifest's RUN_COMMAND block is the SAME absolute-path invocation — not `./run` — so the planner can run it programmatically too. Use `$HOME/.whetstone/lessons/YYYY-MM-DD/<test-file>` (absolute) rather than relative paths in both places.

8. Do NOT mention ticket numbers, dates beyond the lesson header, author names, "Claude", or any process metadata.

OUTPUT FORMAT — emit EXACTLY this block structure and nothing else (no preamble, no markdown fences around the whole thing):

=== RUN_COMMAND ===
<the single shell command that runs the test from ~/.whetstone>
=== SCAFFOLD_FILES ===
<one filename per line — files the learner is meant to edit, scaffolds only, NOT the test or README>
=== FILE: README.md ===
<full README content>
=== FILE: scratch.md ===
# Scratchpad — for your notes




=== FILE: <next filename> ===
<full file content verbatim>
=== FILE: <next filename> ===
<full file content verbatim>
... (continue for every file)
=== END ===

Output begins on the next line.
"""


MANIFEST_BLOCK_RE = re.compile(r"^===\s*(.+?)\s*===\s*$", re.MULTILINE)


def parse_manifest(text: str) -> dict | None:
    """Parse the model's RUN_COMMAND / SCAFFOLD_FILES / FILE: ... / END manifest.

    Returns {"run_command": str, "scaffold_files": [str], "files": {name: content}}
    or None on parse failure.
    """
    # Strip any leading prose / fences.
    lines = text.splitlines()
    start = 0
    for i, ln in enumerate(lines):
        if MANIFEST_BLOCK_RE.fullmatch(ln):
            start = i
            break
    text = "\n".join(lines[start:])

    sections: list[tuple[str, str]] = []
    last_idx = 0
    last_header = None
    for m in MANIFEST_BLOCK_RE.finditer(text):
        if last_header is not None:
            body = text[last_idx:m.start()].rstrip("\n")
            sections.append((last_header, body))
        last_header = m.group(1).strip()
        last_idx = m.end() + 1
    if last_header is not None and last_header != "END":
        body = text[last_idx:].rstrip("\n")
        sections.append((last_header, body))

    out = {"run_command": "", "scaffold_files": [], "files": {}}
    for header, body in sections:
        if header == "END":
            break
        if header == "RUN_COMMAND":
            out["run_command"] = body.strip()
        elif header == "SCAFFOLD_FILES":
            out["scaffold_files"] = [ln.strip() for ln in body.splitlines() if ln.strip()]
        elif header.startswith("FILE:"):
            fname = header[len("FILE:"):].strip()
            out["files"][fname] = body
        else:
            sys.stderr.write(f"warning: unknown manifest section '{header}'\n")
    if not out["files"] or not out["run_command"]:
        return None
    return out


def resolve_claude() -> str | None:
    """Find the claude CLI without trusting launchd's minimal PATH."""
    candidates = [
        shutil.which("claude"),
        str(Path.home() / ".local" / "bin" / "claude"),
        "/opt/homebrew/bin/claude",
        "/usr/local/bin/claude",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


CLAUDE_TIMEOUT_S = int(os.environ.get("WHETSTONE_CLAUDE_TIMEOUT", "1200"))
CLAUDE_MODEL = os.environ.get("WHETSTONE_CLAUDE_MODEL", "sonnet")


def call_claude(prompt: str) -> str | None:
    claude_bin = resolve_claude()
    if claude_bin is None:
        return None
    # --strict-mcp-config with no --mcp-config disables every MCP server, so
    # the headless run never blocks on plugin MCP health checks. Pin a fast
    # model (sonnet by default) — lesson rendering is well-scoped and the
    # default Opus session is slow enough to blow the timeout intermittently.
    cmd = [claude_bin, "-p", "--strict-mcp-config"]
    if CLAUDE_MODEL:
        cmd += ["--model", CLAUDE_MODEL]
    cmd.append(prompt)
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"claude CLI timed out after {CLAUDE_TIMEOUT_S}s\n")
        return None
    except FileNotFoundError:
        sys.stderr.write(f"claude CLI not found at {claude_bin}\n")
        return None
    if r.returncode != 0:
        sys.stderr.write(f"claude CLI exited {r.returncode}: {r.stderr[:500]}\n")
        return None
    return r.stdout.strip()


def render_fallback(topic, sources, lesson_dir, language, mode) -> dict:
    """Minimal usable lesson when Claude is unavailable."""
    src_lines = []
    for sid in topic.sources:
        s = sources.get(sid, {})
        bits = [s.get("title", sid), s.get("url", "")]
        src_lines.append("- " + " — ".join(b for b in bits if b))
    refs = "\n".join(src_lines) or "- (no references seeded)"

    rel = lesson_dir.relative_to(STATE).as_posix()
    if language == "ruby":
        test_name = "lesson_spec.rb"
        scaffold = "lesson.rb"
        run_cmd = f"cd ~/.whetstone && bundle exec rspec {rel}/{test_name}"
        scaffold_body = "# TODO: implement\n"
        test_body = "require_relative 'lesson'\n\nRSpec.describe '{}' do\n  it 'is implemented' do\n    expect(true).to be(false)\n  end\nend\n".format(topic.title)
    else:
        test_name = "lesson.test.ts"
        scaffold = "lesson.ts"
        run_cmd = f"cd ~/.whetstone && npx vitest run {rel}/{test_name}"
        scaffold_body = "// TODO: implement\nexport {};\n"
        test_body = "import { describe, expect, it } from 'vitest';\n\ndescribe('" + topic.title + "', () => {\n  it.todo('Claude CLI was unavailable — write the test manually');\n});\n"

    readme = (
        f"# {topic.title}\n\n## Concept\n\n{topic.summary}\n\n"
        f"_(Claude CLI was unavailable when this lesson was generated; concept body wasn't filled in. Skim the references and try anyway.)_\n\n"
        f"## How to run this lesson\n\n```\n{run_cmd}\n```\n\n"
        f"## References\n\n{refs}\n"
    )

    return {
        "run_command": run_cmd,
        "scaffold_files": [scaffold],
        "files": {
            "README.md": readme,
            "scratch.md": "# Scratchpad — for your notes\n\n\n\n",
            scaffold: scaffold_body,
            test_name: test_body,
        },
    }


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--topic", default=None)
    ap.add_argument("--language", default=None)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if not STATE.exists():
        sys.stderr.write(f"State directory {STATE} not found. Run scripts/install.sh first.\n")
        return 2

    today = dt.date.today()
    today_dir = LESSONS / today.isoformat()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    catalog = load_catalog()
    sources = load_sources()
    kmap    = load_kmap()
    state   = load_state()

    y_signal = update_kmap_for_yesterday(kmap, today)
    save_kmap(kmap)

    language = args.language or pick_language(state, today)

    if today_dir.exists() and not args.force:
        meta = load_lesson_meta(today_dir)
        if meta:
            print(f"Today's lesson already exists at {today_dir}")
            print(f"  topic: {meta.get('topic_id')} ({meta.get('mode')}, {meta.get('language')})")
            if not args.no_open:
                open_in_editor(today_dir)
            return 0

    override_hint = args.topic
    if override_hint is None and y_signal:
        override_hint = y_signal.get("scratch_next")

    topic, mode = pick_topic(catalog, kmap, state, language, today, override_hint, rng)

    yesterday_note = (y_signal or {}).get("scratch_text") or None
    prompt = build_prompt(topic, sources, language, mode, today_dir, yesterday_note)

    rendered = call_claude(prompt)
    manifest = parse_manifest(rendered) if rendered else None
    if manifest is None:
        sys.stderr.write("Claude unavailable or manifest unparsable — writing fallback.\n")
        manifest = render_fallback(topic, sources, today_dir, language, mode)

    # Wipe any pre-existing dir content if --force.
    if args.force and today_dir.exists():
        shutil.rmtree(today_dir)
    today_dir.mkdir(parents=True, exist_ok=True)

    for fname, content in manifest["files"].items():
        out_path = today_dir / fname
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content if content.endswith("\n") else content + "\n")
        if fname == "run" or fname.endswith(".sh"):
            out_path.chmod(0o755)

    now_iso = dt.datetime.now().isoformat()
    meta = {
        "topic_id":         topic.id,
        "title":            topic.title,
        "section":          topic.section,
        "mode":             mode,
        "language":         language,
        "generated_at":     today.isoformat(),
        "generated_at_iso": now_iso,
        "run_command":      manifest["run_command"],
        "scaffold_files":   manifest["scaffold_files"],
    }
    (today_dir / "lesson.json").write_text(json.dumps(meta, indent=2))

    print(f"✓ {today_dir}")
    print(f"  topic: {topic.id}  ({mode}, {language})")
    print(f"  run:   {manifest['run_command']}")

    if not args.no_open:
        open_in_editor(today_dir)

    return 0


def open_in_editor(path: Path) -> None:
    """Open the lesson dir in VS Code if available."""
    if shutil.which("code"):
        subprocess.run(["code", str(path)], check=False)
    elif shutil.which("open"):
        subprocess.run(["open", str(path)], check=False)


if __name__ == "__main__":
    sys.exit(main())
