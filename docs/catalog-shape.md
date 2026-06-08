# Catalog shape

The whetstone catalog is the universe of topics the planner can draw from. Each topic is the **seed** of a lesson — not the lesson itself. Detailed lesson content is generated at lesson-time by the planner; the catalog just needs to be enough for the planner to know what to teach and where to send the learner for primary sources.

Two files make up the catalog:

- `catalog/topics.yml` — the topic list.
- `catalog/sources.yml` — the citation library that topics reference by `id`.

Both files live in the repo (`~/whetstone/catalog/`) as the canonical seed, and are copied into the user's state directory (`~/.whetstone/catalog/`) by `scripts/install.sh`. The planner reads from the state copy, so the user can edit it locally without dirtying the repo.

## topics.yml schema

```yaml
topics:
  - id:        kebab-case-stable-identifier
    title:     "Human-readable lesson title"
    section:   top-level-section-id           # used for exploration bucketing
    summary:   "One-line description."
    prereqs:   [other-topic-id, ...]          # optional
    related:   [other-topic-id, ...]          # optional
    sources:   [source-id-from-sources-yml]   # optional
    languages: [typescript, ruby, any]        # optional (default: any)
    tags:      [theory, hands-on, classic]    # optional, free-form
```

### Field notes

- **`id`** — stable kebab-case identifier. The knowledge map keys off this. Once a user has engaged with a topic, changing its id orphans the engagement record. Treat ids as append-only after launch.
- **`title`** — what shows up in the lesson header. Be specific; "Singletons" is worse than "Singleton pattern — and why people grew to hate it".
- **`section`** — the top-level bucket. The planner uses section coverage to detect "never-explored territory" for exploration days. Twelve to fifteen sections is the sweet spot — coarse enough to be meaningful, fine-grained enough to be exploration signal.
- **`summary`** — one line. Goes into the planner's prompt to Claude when generating the lesson. Treat it as the elevator pitch for the topic.
- **`prereqs` / `related`** — currently informational. Future planner versions may use prereqs to delay topics until their dependencies are confident.
- **`sources`** — list of ids from `sources.yml`. Claude weaves these into the References block of the generated lesson, with URLs where available.
- **`languages`** — restricts which language a topic can be taught in. Most concepts are `any` (the default). Use this for genuinely language-specific topics (`ts-conditional-types`, `ruby-method-missing-and-respond-to`).
- **`tags`** — free-form. `theory`, `hands-on`, `classic`, `advanced`, `async`, `type-systems` are the conventions in the seed catalog. Tags aren't currently weighted by the planner but the prompt surfaces them to Claude.

## sources.yml schema

```yaml
sources:
  - id:      kebab-case-id
    title:   "Full title"
    authors: ["Author One", "Author Two"]   # optional
    year:    2017                            # optional
    kind:    book | paper | rfc | web        # optional
    url:     "https://..."                   # optional but recommended
```

The seed catalog's source library is the classics — GoF, PEAA, DDIA, Refactoring, the foundational distributed-systems papers, key RFCs, and a small set of always-live web references (MDN, refactoring.guru, Fowler's bliki). Add new sources here before referencing them from a topic.

## Authoring a new topic

1. Pick a stable `id`. Check that no existing topic uses it.
2. Pick a `section`. Reuse an existing section if one fits; only invent a new section if the topic genuinely doesn't belong anywhere in the current taxonomy.
3. Add or reuse `sources` entries. Don't reference a source from a topic without first adding it to `sources.yml`.
4. Write the `summary` as if you're pitching a senior engineer the lesson in one line. Concrete > abstract.
5. Test it: run `~/whetstone/scripts/generate-lesson.sh --topic <your-new-id> --force` to see the lesson Claude generates from your seed.

## Repurposing for non-code domains

The catalog format is intentionally generic. If you want to repurpose whetstone for, say, learning music theory or history:

1. Build a custom `topics.yml` with sections and topics that match your domain.
2. Build a custom `sources.yml` with the canonical references in your domain.
3. Run `/whetstone:reseed-catalog` and point at your custom file.
4. Edit `~/.whetstone/state.json` to set `current_language` to a language that fits (this controls which template gets used — keep it as `typescript` if you want code blocks, or extend templates if you don't).
5. Re-bootstrap to recalibrate the knowledge map.

The lesson rendering still assumes a code-shaped file (a comment block, a "your code here" zone, a failing test). If your domain doesn't fit that, you'll want to add a new template under `templates/` and extend `scripts/plan_and_generate.py` to pick it.

## Catalog size guidance

The seed catalog ships ~120 topics across 13 sections. That's deliberately dense — the planner picks one per day, so even at 5 lessons per week the catalog supports a year of reinforcement plus exploration without running dry. There's no harm in growing it; the per-topic cost is 5-10 lines of YAML and the planner's selection logic doesn't care how big the pool is.

The cap is human, not technical: a catalog you can't skim in five minutes is too big to curate. If you find yourself wanting to add a 200th topic, ask whether some existing topic should generalize to absorb it.
