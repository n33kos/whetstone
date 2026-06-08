#!/usr/bin/env python3
"""
Whetstone planner + generator.

Reads the catalog and knowledge map, picks a topic for today (or honors an
override), invokes Claude to render the lesson content from a template,
writes it to ~/.whetstone/lessons/YYYY-MM-DD/lesson.{ts,rb}, and opens it
in VS Code.

Entry point for both the launchd cron and the /whetstone:generate skill.
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
        (p for p in LESSONS.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)),
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


SCRATCH_NEXT_RE = re.compile(r"^\s*(?://|#)?\s*NEXT:\s*(.+?)\s*$", re.MULTILINE)


def parse_scratchpad(lesson_path: Path) -> dict[str, Any]:
    """Pull the scratchpad section out of a lesson file and look for NEXT:.

    Returns {"text": str, "next": str | None}.
    """
    text = lesson_path.read_text(errors="replace")
    # Scratchpad starts at the literal `scratch:` marker (in either lang).
    m = re.search(r"(?://|#)\s*scratch:\s*\n(.*)$", text, re.DOTALL)
    body = m.group(1) if m else ""
    nxt = SCRATCH_NEXT_RE.search(body)
    return {"text": body.strip(), "next": (nxt.group(1).strip() if nxt else None)}


def extract_topic_id(lesson_path: Path) -> str | None:
    """Pull the topic id out of the lesson header comment."""
    text = lesson_path.read_text(errors="replace")
    m = re.search(r"Topic id:\s*(\S+)", text)
    return m.group(1) if m else None


def run_test(lesson_path: Path, timeout: int = 30) -> bool | None:
    """Best-effort: run the lesson's test and return True/False/None.

    None means the test runner couldn't be invoked (don't penalize).
    """
    suffix = lesson_path.suffix
    try:
        if suffix == ".ts":
            r = subprocess.run(
                ["npx", "--prefix", str(STATE), "vitest", "run", str(lesson_path)],
                cwd=STATE, capture_output=True, timeout=timeout, text=True,
            )
        elif suffix == ".rb":
            r = subprocess.run(
                ["bundle", "exec", "rspec", str(lesson_path)],
                cwd=STATE,
                env={**os.environ, "BUNDLE_GEMFILE": str(STATE / "Gemfile")},
                capture_output=True, timeout=timeout, text=True,
            )
        else:
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    return r.returncode == 0


def code_was_edited(lesson_path: Path) -> bool:
    """True if anything was written between the "your code here" markers."""
    text = lesson_path.read_text(errors="replace")
    m = re.search(
        r"▼ your code here ▼(.*?)▲ your code here ▲",
        text, re.DOTALL,
    )
    if not m:
        return False
    body = m.group(1)
    # Strip the framing comments and look for non-blank, non-comment lines
    # that aren't the placeholder scaffold.
    real = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("//") or s.startswith("#"):
            continue
        if "YOUR_CODE_SCAFFOLD" in s or s in ("{}", "{};"):
            continue
        real.append(s)
    return len(real) > 0


# ──────────────────────────────────────────────────────────────────────────
# Knowledge map update
# ──────────────────────────────────────────────────────────────────────────

def update_kmap_for_yesterday(kmap: dict, today: dt.date) -> dict[str, Any] | None:
    """Inspect yesterday's lesson and roll its signal into the knowledge map.

    Returns a dict describing what happened, or None if there was no
    prior lesson to inspect.
    """
    ydir = yesterday_dir(today)
    if ydir is None:
        return None

    files = list(ydir.glob("lesson.*"))
    if not files:
        return None
    lesson = files[0]

    tid = extract_topic_id(lesson)
    if not tid:
        return None

    engaged = code_was_edited(lesson)
    result = run_test(lesson) if engaged else None
    scratch = parse_scratchpad(lesson)

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
            entry["confidence"] = min(1.0, entry.get("confidence", 0.0) + 0.25)
            # Next review pushed out ~ 2^completions days, capped at 60.
            gap = min(60, 2 ** entry["completions"])
        else:
            # Engaged but didn't pass — concept exposure still earns a nudge.
            entry["confidence"] = min(1.0, entry.get("confidence", 0.0) + 0.10)
            gap = 3
        next_review = dt.date.fromisoformat(ydir.name) + dt.timedelta(days=gap)
        entry["next_review_at"] = next_review.isoformat()
    # If not engaged, log no signal — leave confidence and next_review alone.

    return {
        "topic_id": tid,
        "engaged": engaged,
        "test_passed": result,
        "scratch_next": scratch["next"],
    }


# ──────────────────────────────────────────────────────────────────────────
# Topic selection
# ──────────────────────────────────────────────────────────────────────────

def pick_topic(
    catalog: dict[str, Topic],
    kmap: dict,
    state: dict,
    language: str,
    today: dt.date,
    override_hint: str | None,
    rng: random.Random,
) -> tuple[Topic, str]:
    """Pick today's topic. Returns (topic, mode)."""
    topics = kmap.get("topics", {})
    eligible = [t for t in catalog.values() if language in t.languages or "any" in t.languages]
    if not eligible:
        eligible = list(catalog.values())

    # 1. Honor scratchpad NEXT: or explicit hint.
    if override_hint:
        match = resolve_hint(override_hint, eligible)
        if match:
            return match, "override"

    # 2. Exploration cadence — every Nth day, force a never-seen topic.
    cadence = int(state.get("exploration_cadence_days", 7))
    if cadence > 0 and (today.toordinal() % cadence == 0):
        unseen = [t for t in eligible if t.id not in topics]
        if unseen:
            return rng.choice(unseen), "exploration"

    # 3. Reinforcement: weight by (1 - confidence) and forgetting curve.
    focus = set(state.get("current_focus_areas", []) or [])

    def score(t: Topic) -> float:
        entry = topics.get(t.id)
        if entry is None:
            base = 0.55  # mid — never seen leans slightly toward exploration
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
    # Soften determinism: pick from the top 12 with weighted random.
    top = weights[:12]
    chosen = rng.choices([t for _, t in top], weights=[s for s, _ in top], k=1)[0]
    return chosen, "reinforcement"


def resolve_hint(hint: str, pool: list[Topic]) -> Topic | None:
    """Match a scratchpad NEXT: hint against the catalog.

    Tries exact id match first, then case-insensitive substring against
    id / title / section.
    """
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


# ──────────────────────────────────────────────────────────────────────────
# Language selection
# ──────────────────────────────────────────────────────────────────────────

def pick_language(state: dict, today: dt.date) -> str:
    primary = state.get("current_language", "typescript")
    secondary = state.get("secondary_language", "ruby")
    cadence = int(state.get("ruby_cadence_days", 0))
    if cadence > 0 and (today.toordinal() % cadence == 0):
        return secondary
    return primary


# ──────────────────────────────────────────────────────────────────────────
# Lesson rendering
# ──────────────────────────────────────────────────────────────────────────

def build_prompt(
    topic: Topic,
    sources: dict[str, dict],
    template: str,
    language: str,
    mode: str,
    lesson_path: Path,
    yesterday_note: str | None,
) -> str:
    """The single prompt sent to Claude to render the lesson."""
    src_lines = []
    for sid in topic.sources:
        s = sources.get(sid)
        if not s:
            continue
        author = ", ".join(s.get("authors", [])) if s.get("authors") else ""
        year = s.get("year", "")
        url = s.get("url", "")
        bits = [b for b in (author, str(year) if year else "", s.get("title", ""), url) if b]
        src_lines.append(" — ".join(bits))
    sources_block = "\n".join(f"  - {line}" for line in src_lines) or "  - (no citations seeded; you may add canonical ones)"

    yesterday_block = (
        f"\nYesterday's scratchpad note from the learner:\n  \"{yesterday_note}\"\n"
        f"Where appropriate, gently respond to what they wrote in the concept body."
    ) if yesterday_note else ""

    return f"""You are generating today's whetstone lesson — a single-file, copy-paste-runnable code lesson.

The lesson must be returned as the FULL CONTENTS of the file, nothing else. No preamble, no commentary, no markdown fences. Just the raw file contents, ready to write to disk.

Use the template below VERBATIM as your output structure. Replace every {{{{PLACEHOLDER}}}} with appropriate content. Keep all comment framing, run-instructions, marker bars, and the scratchpad block intact.

Topic to teach today:
  id:       {topic.id}
  title:    {topic.title}
  section:  {topic.section}
  summary:  {topic.summary}
  mode:     {mode}
  language: {language}
  tags:     {", ".join(topic.tags) or "(none)"}

Canonical references for this topic (use these in the References block):
{sources_block}
{yesterday_block}

Placeholder fill instructions:

  {{{{DATE}}}}             — today's ISO date
  {{{{TOPIC_TITLE}}}}      — exactly "{topic.title}"
  {{{{SECTION}}}}          — exactly "{topic.section}"
  {{{{MODE}}}}             — exactly "{mode}"
  {{{{TOPIC_ID}}}}         — exactly "{topic.id}"
  {{{{LESSON_PATH}}}}      — exactly "{lesson_path}"

  {{{{CONCEPT_BODY}}}}     — 5-10 sentences explaining the concept with precision.
                             Aim for the "tightest correct explanation a senior eng
                             would respect." No fluff, no marketing tone. Use
                             concrete examples and name specific systems where
                             applicable. Wrap lines around column 80.

  {{{{WHY_IT_MATTERS}}}}   — 2-4 sentences on what this unlocks for the learner.
                             Concrete failure modes it prevents or capabilities
                             it enables.

  {{{{REAL_WORLD_EXAMPLES}}}} — 2-4 short bullets (each line prefixed with " * ")
                                naming real production systems, libraries, or
                                incidents where this concept showed up.

  {{{{REFERENCES}}}}       — bulleted references built from the citations above.
                             Each line prefixed with " * ". Include URLs where given.

  {{{{YOUR_CODE_HERE_HINT}}}} — one or two sentences hinting at the shape of what
                                they need to implement, without giving it away.

  {{{{YOUR_CODE_SCAFFOLD}}}} — empty function / class signatures the learner will
                               fill in. The scaffold must compile (or parse) but
                               the test must fail until they implement it. For
                               TypeScript, use `export` and explicit types so the
                               test can import. For Ruby, declare the class/method
                               with a stub body that raises NotImplementedError
                               or returns nil.

  {{{{TEST_BODY}}}}        — a failing test block. For TypeScript use Vitest's
                             `it(...)` / `expect(...)`. For Ruby use RSpec
                             `it ... do ... expect(...).to eq(...) end`. The test
                             must:
                               1. Import / reference the symbols the scaffold
                                  declares.
                               2. Assert behavior that's pedagogically tied to
                                  the concept above — not just any test.
                               3. Be runnable as-is and fail until the learner
                                  implements the scaffold.
                             Indent the inner `it` block to match the surrounding
                             describe context.

Hard rules:
  * Output ONLY the file contents. No prose around it. No fenced code blocks.
  * Use the template's existing comment style (// for TS, # for Ruby).
  * Keep the file under ~150 lines total.
  * The scratchpad section at the bottom must be preserved verbatim, including
    the "scratch:" marker and the empty lines after it.
  * Do NOT add a date/author/PR/ticket signature anywhere in the file.

Template to fill in (DO NOT alter anything outside the {{{{PLACEHOLDERS}}}}):

────────────────── TEMPLATE BEGIN ──────────────────
{template}
─────────────────── TEMPLATE END ───────────────────
"""


def call_claude(prompt: str) -> str | None:
    """Invoke the `claude` CLI to generate the lesson contents.

    Returns the model's output, or None if the CLI is unavailable.
    """
    if shutil.which("claude") is None:
        return None
    try:
        r = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=180,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if r.returncode != 0:
        sys.stderr.write(f"claude CLI failed: {r.stderr}\n")
        return None
    return r.stdout.strip()


def render_fallback(template: str, topic: Topic, sources: dict, **fields: str) -> str:
    """Mechanical template fill — used if Claude is unavailable.

    Produces a usable-but-skeletal lesson that the user can flesh out manually.
    """
    src_lines = []
    for sid in topic.sources:
        s = sources.get(sid, {})
        bits = [s.get("title", sid), s.get("url", "")]
        src_lines.append(" * " + " — ".join(b for b in bits if b))
    refs = "\n".join(src_lines) or " * (no references seeded)"

    body = template
    repl = {
        "DATE": fields["DATE"],
        "TOPIC_TITLE": topic.title,
        "SECTION": topic.section,
        "MODE": fields["MODE"],
        "TOPIC_ID": topic.id,
        "LESSON_PATH": fields["LESSON_PATH"],
        "CONCEPT_BODY": (
            f"{topic.summary}\n *\n * [Claude CLI was unavailable when this lesson was "
            f"generated, so the concept body wasn't filled in. Skim the references "
            f"below and try the test anyway — that's still useful.]"
        ),
        "WHY_IT_MATTERS": "(fallback — fill in manually)",
        "REAL_WORLD_EXAMPLES": " * (fallback — fill in manually)",
        "REFERENCES": refs,
        "YOUR_CODE_HERE_HINT": "Read the failing test below — its assertions describe what to build.",
        "YOUR_CODE_SCAFFOLD": "// TODO: scaffold not generated (Claude unavailable). Write whatever symbols the test needs.",
        "TEST_BODY": "  it.todo('Claude was unavailable — write a test or copy from the references');",
    }
    for k, v in repl.items():
        body = body.replace("{{" + k + "}}", v)
    return body


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="Generate even if today's lesson already exists (overwrites).")
    ap.add_argument("--topic", default=None,
                    help="Override topic selection with a specific topic id or hint.")
    ap.add_argument("--language", default=None,
                    help="Override language selection (typescript or ruby).")
    ap.add_argument("--no-open", action="store_true",
                    help="Skip opening the lesson in VS Code.")
    ap.add_argument("--seed", type=int, default=None,
                    help="Deterministic RNG seed (for testing).")
    args = ap.parse_args()

    if not STATE.exists():
        sys.stderr.write(f"State directory {STATE} not found. Run scripts/install.sh first.\n")
        return 2

    today = dt.date.today()
    today_dir = LESSONS / today.isoformat()
    lesson_ext_default = ".ts"

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    catalog = load_catalog()
    sources = load_sources()
    kmap    = load_kmap()
    state   = load_state()

    # Roll yesterday's signal into the knowledge map.
    y_signal = update_kmap_for_yesterday(kmap, today)
    save_kmap(kmap)

    # Pick language and topic.
    language = args.language or pick_language(state, today)
    ext      = ".rb" if language == "ruby" else ".ts"
    lesson_path = today_dir / f"lesson{ext}"

    if lesson_path.exists() and not args.force:
        print(f"Today's lesson already exists at {lesson_path}")
        if not args.no_open:
            open_in_editor(lesson_path)
        return 0

    override_hint = args.topic
    if override_hint is None and y_signal:
        override_hint = y_signal.get("scratch_next")

    topic, mode = pick_topic(catalog, kmap, state, language, today, override_hint, rng)

    # Load the template for this language.
    template_name = "lesson-typescript.ts" if language != "ruby" else "lesson-ruby.rb"
    template = (REPO / "templates" / template_name).read_text()

    yesterday_note = None
    if y_signal:
        ydir = yesterday_dir(today)
        if ydir:
            scratch_files = list(ydir.glob("lesson.*"))
            if scratch_files:
                yesterday_note = parse_scratchpad(scratch_files[0]).get("text") or None

    prompt = build_prompt(topic, sources, template, language, mode, lesson_path, yesterday_note)

    # Render via Claude (with fallback).
    rendered = call_claude(prompt)
    if not rendered:
        sys.stderr.write("Claude CLI unavailable — writing fallback scaffold.\n")
        rendered = render_fallback(
            template, topic, sources,
            DATE=today.isoformat(),
            MODE=mode,
            LESSON_PATH=str(lesson_path),
        )

    # Write file.
    today_dir.mkdir(parents=True, exist_ok=True)
    lesson_path.write_text(rendered)
    print(f"✓ {lesson_path}")
    print(f"  topic: {topic.id}  ({mode}, {language})")

    if not args.no_open:
        open_in_editor(lesson_path)

    return 0


def open_in_editor(path: Path) -> None:
    """Open the lesson in VS Code if available, falling back to `open`."""
    if shutil.which("code"):
        subprocess.run(["code", str(path)], check=False)
    elif shutil.which("open"):
        subprocess.run(["open", str(path)], check=False)


if __name__ == "__main__":
    sys.exit(main())
