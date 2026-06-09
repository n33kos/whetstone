#!/usr/bin/env bash
# whetstone install — one-time setup.
#
# Creates ~/.whetstone/ state directory, installs shared dev deps
# (Vitest for TypeScript, RSpec for Ruby), seeds the catalog, writes
# initial state files, and installs the launchd plist that fires the
# daily 7am lesson generator.
#
# Idempotent. Safe to re-run.

set -euo pipefail

REPO="${WHETSTONE_REPO:-$HOME/whetstone}"
STATE="${WHETSTONE_STATE:-$HOME/.whetstone}"
LABEL="com.whetstone.daily"
PLIST_DST="$HOME/Library/LaunchAgents/${LABEL}.plist"

say() { printf '\033[1;36m›\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

[[ -d "$REPO" ]] || die "Repo not found at $REPO (set WHETSTONE_REPO to override)."
command -v node >/dev/null 2>&1 || die "node is required but not found on PATH."
command -v npm >/dev/null 2>&1 || die "npm is required but not found on PATH."

say "Creating state directory at $STATE"
mkdir -p "$STATE"/{lessons,logs}

# ─── Python venv via uv (pinned, so launchd's PATH can't trip us) ───────
UV_BIN=""
for candidate in "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv "$(command -v uv || true)"; do
  if [[ -x "$candidate" ]]; then UV_BIN="$candidate"; break; fi
done
[[ -n "$UV_BIN" ]] || die "uv is required but not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"

if [[ ! -x "$STATE/.venv/bin/python3" ]]; then
  say "Creating Python venv at $STATE/.venv (via uv)"
  (cd "$STATE" && "$UV_BIN" venv .venv --quiet)
fi
say "Installing pyyaml into the whetstone venv (via uv)"
"$UV_BIN" pip install --python "$STATE/.venv/bin/python3" --quiet pyyaml

# ─── TypeScript / Vitest shared install ──────────────────────────────────
if [[ ! -f "$STATE/package.json" ]]; then
  say "Initializing shared TypeScript install"
  cat > "$STATE/package.json" <<'JSON'
{
  "name": "whetstone-lessons",
  "private": true,
  "version": "0.0.0",
  "description": "Shared dev deps for whetstone lessons. Not published.",
  "type": "module",
  "scripts": {
    "test": "vitest run"
  }
}
JSON
fi

if [[ ! -f "$STATE/vitest.config.ts" ]]; then
  say "Writing vitest config (lesson.ts include pattern)"
  cat > "$STATE/vitest.config.ts" <<'TSCONFIG'
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Whetstone lessons live at lessons/YYYY-MM-DD/lesson.ts — they're not
    // *.test.ts because the file IS the lesson. Match the lesson naming.
    include: ['lessons/**/lesson.ts'],
  },
});
TSCONFIG
fi

say "Installing Vitest + TS toolchain (npm install in $STATE)"
(cd "$STATE" && npm install --silent --save-dev \
  vitest@^2 \
  typescript@^5 \
  @types/node@^22 \
  tsx@^4)

# ─── Ruby / RSpec shared install ─────────────────────────────────────────
if command -v bundle >/dev/null 2>&1; then
  if [[ ! -f "$STATE/Gemfile" ]]; then
    say "Initializing shared Ruby install"
    cat > "$STATE/Gemfile" <<'GEMFILE'
source "https://rubygems.org"

gem "rspec", "~> 3.13"
GEMFILE
  fi
  say "Installing RSpec (bundle install in $STATE)"
  (cd "$STATE" && bundle install --quiet)
else
  warn "bundler not found — skipping Ruby setup. Install with: gem install bundler"
fi

# ─── Catalog seed ────────────────────────────────────────────────────────
if [[ ! -f "$STATE/catalog/topics.yml" ]]; then
  say "Seeding catalog from $REPO/catalog/"
  mkdir -p "$STATE/catalog"
  cp "$REPO/catalog/topics.yml"  "$STATE/catalog/topics.yml"
  cp "$REPO/catalog/sources.yml" "$STATE/catalog/sources.yml"
else
  say "Catalog already present in state — leaving in place (run /whetstone:reseed-catalog to refresh)"
fi

# ─── Knowledge map + state.json ──────────────────────────────────────────
if [[ ! -f "$STATE/knowledge-map.yml" ]]; then
  say "Creating empty knowledge map"
  cat > "$STATE/knowledge-map.yml" <<'YML'
# Per-topic confidence + scheduling.
#
# Each entry:
#   <topic-id>:
#     confidence: 0.0-1.0       (0 = "never seen", 1 = "I could teach this")
#     last_seen_at: ISO-8601 date
#     next_review_at: ISO-8601 date
#     engagements: integer (lessons attempted, regardless of test result)
#     completions: integer (lessons where the user made the test pass)
#
# The /whetstone:bootstrap skill populates initial confidence scores
# from a conversational self-assessment. Unmentioned topics start
# implicit — absent from this map — and the planner treats them as
# "exploration territory".

topics: {}
YML
fi

if [[ ! -f "$STATE/state.json" ]]; then
  say "Creating user state file"
  cat > "$STATE/state.json" <<'JSON'
{
  "current_language": "typescript",
  "secondary_language": "ruby",
  "ruby_cadence_days": 5,
  "exploration_cadence_days": 7,
  "current_focus_areas": [],
  "goals": [],
  "bootstrap_completed_at": null
}
JSON
fi

# ─── launchd plist ───────────────────────────────────────────────────────
say "Installing launchd plist at $PLIST_DST"
mkdir -p "$(dirname "$PLIST_DST")"
HOME_ESC=$(printf '%s' "$HOME"  | sed 's:/:\\/:g')
REPO_ESC=$(printf '%s' "$REPO"  | sed 's:/:\\/:g')
STATE_ESC=$(printf '%s' "$STATE" | sed 's:/:\\/:g')

sed \
  -e "s/{{WHETSTONE_REPO}}/${REPO_ESC}/g" \
  -e "s/{{WHETSTONE_STATE}}/${STATE_ESC}/g" \
  -e "s/{{HOME}}/${HOME_ESC}/g" \
  "$REPO/templates/launchd.plist" > "$PLIST_DST"

# Unload first to avoid "service already loaded" — ignore failure on first install.
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load   "$PLIST_DST"

say "Done. Cron will fire daily at 07:00 local time."
say "To generate a lesson right now: $REPO/scripts/generate-lesson.sh"
