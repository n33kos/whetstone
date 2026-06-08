# ═══════════════════════════════════════════════════════════════════════════
# Whetstone — {{DATE}}
#
#   Topic:    {{TOPIC_TITLE}}
#   Section:  {{SECTION}}
#   Mode:     {{MODE}}            (reinforcement | exploration)
#   Topic id: {{TOPIC_ID}}
#
# ───────────────────────────────────────────────────────────────────────────
# Run this lesson
#
#   bundle exec --gemfile=$HOME/.whetstone/Gemfile rspec {{LESSON_PATH}}
#
# Or, if your shell is already in `~/.whetstone`:
#
#   bundle exec rspec {{LESSON_PATH}}
# ───────────────────────────────────────────────────────────────────────────
#
# Concept
#
# {{CONCEPT_BODY}}
#
# Why it matters
#
# {{WHY_IT_MATTERS}}
#
# Where it shows up in real systems
#
# {{REAL_WORLD_EXAMPLES}}
#
# References
#
# {{REFERENCES}}
#
# ═══════════════════════════════════════════════════════════════════════════

require 'rspec/autorun'

# ───────────────────────────────────────────────────────────────────────────
# ▼ your code here ▼
#
# Implement whatever the failing test below is asking for.
#
# {{YOUR_CODE_HERE_HINT}}

{{YOUR_CODE_SCAFFOLD}}

# ▲ your code here ▲
# ───────────────────────────────────────────────────────────────────────────


# ───────────────────────────────────────────────────────────────────────────
# ▼ failing test ▼
# Don't edit this block unless you want to change what you're learning.

RSpec.describe '{{TOPIC_TITLE}}' do
{{TEST_BODY}}
end

# ▲ failing test ▲
# ───────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════
# Scratchpad — anything you write below this line is parsed by tomorrow's
# planner. Use it for: questions, half-thoughts, "go deeper on X next time",
# "this connected to Y I read last week", or whatever.
#
# If you want to force tomorrow's topic, write:
#
#     NEXT: <topic-id-or-keywords>
#
# on a line by itself.
# ───────────────────────────────────────────────────────────────────────────

# scratch:
#
#
#
