#!/usr/bin/env bash
#
# build-release-branch.sh — publish the lean `release` branch that users install from.
#
# Why this exists
# ---------------
# `claude plugin marketplace add <repo>` git-clones, in full, whatever branch hosts
# `.claude-plugin/marketplace.json`. That clone lands in the user's
# ~/.claude/plugins/marketplaces/<name>/ cache. If users add `main`, they get the
# entire dev repo (tests/, .github/, caches, CLAUDE.md, …). To keep that footprint
# lean we maintain a separate `release` branch that contains ONLY the plugin runtime
# surface, and point users at it with:
#
#     claude plugin marketplace add https://github.com/HemachandranD/observent.git#release
#
# `main` stays the development branch (tests, CI, docs); this script mirrors just the
# allowlisted paths onto `release`. The plugin's own `source: "./"` then resolves
# against the lean tree with no manifest change.
#
# Usage
# -----
#   scripts/build-release-branch.sh            # dry run: build the lean tree, print its path
#   scripts/build-release-branch.sh --push     # build AND force-push to <remote>/release
#
# Env overrides:
#   RELEASE_BRANCH   target branch name          (default: release)
#   RELEASE_REMOTE   remote to push to           (default: origin)
#   RELEASE_PUSH_URL explicit push URL           (CI sets this to a token-auth URL)
#   GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL           commit identity (defaults below)
#
set -euo pipefail

RELEASE_BRANCH="${RELEASE_BRANCH:-release}"

# --- allowlist: the ONLY paths shipped to users on the release branch ---------
# Keep this in sync with the plugin runtime surface. Anything not listed here
# (tests/, .github/, pyproject.toml, CLAUDE.md, .mcp.json, caches) stays on main.
RELEASE_PATHS=(
  .claude-plugin       # plugin.json + marketplace.json
  commands             # /observent* slash commands
  skills               # the skill itself (SKILL.md, references/, scripts/)
  assets/logo.svg      # referenced by README (the .gen.py generator stays on main)
  README.md
  LICENSE
  NOTICE
  package.json         # npx skills discovery
)

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
source_sha="$(git rev-parse HEAD)"
source_ref="$(git rev-parse --abbrev-ref HEAD)"

work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }

echo "Building lean '${RELEASE_BRANCH}' tree from ${source_ref} (${source_sha:0:12})"
for p in "${RELEASE_PATHS[@]}"; do
  if [ ! -e "$p" ]; then
    echo "error: allowlisted path missing from repo: $p" >&2
    cleanup
    exit 1
  fi
  mkdir -p "$work/$(dirname "$p")"
  cp -r "$p" "$work/$p"
  echo "  + $p"
done

cd "$work"
git init -q
git checkout -q -b "$RELEASE_BRANCH"
git add -A
git -c user.name="${GIT_AUTHOR_NAME:-observent-release-bot}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-noreply@github.com}" \
    commit -q -m "Release tree synced from ${source_ref} @ ${source_sha}"

if [ "${1:-}" = "--push" ]; then
  push_url="${RELEASE_PUSH_URL:-$(git -C "$repo_root" remote get-url "${RELEASE_REMOTE:-origin}")}"
  echo "Force-pushing lean tree -> ${RELEASE_BRANCH}"
  # Orphan single-commit branch, replaced each release. The distribution branch
  # holds no hand-authored history, so a force-push is intentional and safe.
  git push -f "$push_url" "$RELEASE_BRANCH"
  cleanup
  echo "Done. Users installing from '#${RELEASE_BRANCH}' now get the lean tree."
else
  echo
  echo "Dry run — lean tree built at:"
  echo "  $work"
  echo "Inspect it, then re-run with --push to publish to ${RELEASE_REMOTE:-origin}/${RELEASE_BRANCH}."
  # Intentionally leave $work in place for inspection on a dry run.
fi
