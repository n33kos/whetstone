---
name: whetstone:reseed-catalog
description: Reset the whetstone catalog. Defaults to reloading the default code-focused catalog from the repo, but accepts a custom catalog file path for non-code repurposing. Idempotent. Triggers on "/whetstone:reseed-catalog", "reset the catalog", "reload whetstone topics", "swap whetstone catalog", "use a custom catalog".
---

# whetstone:reseed-catalog

Replace `~/.whetstone/catalog/topics.yml` (and optionally `sources.yml`) with a fresh copy. Default behavior is "reload from the repo"; the optional path argument lets the user swap in a custom catalog (e.g., for a non-code learning domain).

## Step 1 — Ask what the user wants

Ask:

> "Two options:
> 1. **Reload the default code-focused catalog** from `~/whetstone/catalog/` — useful if you've manually edited the local copy and want to start over.
> 2. **Load a custom catalog** from a path you provide — useful if you're repurposing whetstone for a non-code learning domain (history, math, languages, whatever).
>
> Which one, and if option 2, what's the path?"

Save the choice as `mode` (one of `default` or `custom`) and the path as `custom_path` if applicable.

## Step 2 — Validate

If `mode == custom`, verify that `custom_path` exists and parses as YAML matching the catalog schema (a top-level `topics:` key with a list of entries, each with at minimum `id`, `title`, `section`, `summary`). If validation fails, report the problem and stop.

Read `~/whetstone/docs/catalog-shape.md` for the full schema if needed.

## Step 3 — Back up the existing catalog

Run:

```
cp ~/.whetstone/catalog/topics.yml  ~/.whetstone/catalog/topics.yml.bak-$(date +%Y%m%d-%H%M%S)
cp ~/.whetstone/catalog/sources.yml ~/.whetstone/catalog/sources.yml.bak-$(date +%Y%m%d-%H%M%S)
```

## Step 4 — Reseed

If `mode == default`:

```
cp ~/whetstone/catalog/topics.yml  ~/.whetstone/catalog/topics.yml
cp ~/whetstone/catalog/sources.yml ~/.whetstone/catalog/sources.yml
```

If `mode == custom`:

```
cp "$custom_path" ~/.whetstone/catalog/topics.yml
```

Ask the user whether their custom catalog has a paired `sources.yml`. If yes, copy that too. If no, leave the existing `sources.yml` in place but warn that topic citation rendering may produce gaps.

## Step 5 — Warn about the knowledge map

Topic ids in the knowledge map that no longer exist in the new catalog will be ignored by the planner but still take up space. Ask the user whether to:

- **Leave the knowledge map alone** (safe — old topics just don't get picked).
- **Prune orphaned topic ids** — back up `knowledge-map.yml` first, then remove entries whose ids aren't in the new catalog.

## Step 6 — Confirm

Report the section count and topic count in the new catalog. Suggest running `/whetstone:bootstrap` again if the user just swapped to a custom catalog — confidence scores from the old catalog probably don't translate.
