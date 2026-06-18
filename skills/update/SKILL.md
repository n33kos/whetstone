---
name: whetstone:update
description: Update whetstone to the latest version and refresh its runtime — pulls the newest plugin release, refreshes shared deps, and re-verifies the single daily cron job, all under the hood. No manual cache-path steps. Triggers on "/whetstone:update", "update whetstone", "upgrade whetstone", "get the latest whetstone".
---

# whetstone:update

Update the whetstone plugin and refresh everything it needs, with zero manual steps.

## Step 1 — Run the update script

Run `scripts/update.sh` and save the result as `update_log`.

The script refreshes the n33kos marketplace, runs `claude plugin update whetstone@n33kos` to pull the latest version into a new cache directory, then runs that new version's `install.sh` to refresh shared deps, backfill any new state fields, and re-verify that exactly one launchd job is loaded.

The daily cron points at a stable launcher (`~/.whetstone/run-latest.sh`) that resolves the latest installed version at run time, so the next scheduled lesson adopts the update automatically even without this step — this skill just makes it immediate.

## Step 2 — Report

Surface the new version (from `update_log`) and confirm exactly one launchd job is loaded. If `update_log` warns about job count, tell the user to run `launchctl list | grep whetstone` and offer to help.

## Step 3 — Mention the session caveat

Newly-added or renamed skills load on the next Claude Code session restart (the plugin system applies skill changes at startup). The cron, scripts, catalog, and templates all take effect immediately. Mention this only if the update changed the skill set.
