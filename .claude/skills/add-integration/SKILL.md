---
name: add-integration
description: Scaffold a new observent framework OR backend across every required file in the documented order (detectors, SKILL.md, matrix.md, examples.md, Verified Versions pins, self_host.md, and the docs-consistency test). Use when the user wants to add support for a new agent framework or a new observability backend to the plugin.
disable-model-invocation: true
---

# Add an observent Integration

This is a deliberate, multi-file, side-effecting workflow. It encodes the
"How to Extend" checklists from `CLAUDE.md` so no step is skipped. Drive it as
ordered edits, **show a diff preview before each write**, and finish by running
the test + lint gates.

## Step 0 — Determine what's being added

Ask (or infer from the user's message) which of these it is:

- **A framework** (e.g. a new agent library) → use § Add a Framework.
- **A backend** (a new observability destination) → use § Add a Backend.

Then ask for the specifics you'll need:

- Framework: display name, detector import name, the OpenInference/native
  instrumentor package + exact installed version, which backend its example
  should use.
- Backend: display name, the `oi` vs `otel-genai` convention, required
  package(s) + exact installed versions, endpoint, and whether it has a free
  self-host edition.

Get the **exact installed version** for every pin from the package's PyPI page
or `pip show` — pins in this repo are `==X.Y.Z`, never floors.

## Add a Framework

Edit in this order, diff-previewing each:

1. `skills/observent/scripts/detect_framework.py` — add an entry to `FRAMEWORKS`.
2. `skills/observent/SKILL.md` — add the framework to the Phase 1 §1.2
   argument-hint list **and** the description's auto-invocation triggers.
3. `skills/observent/references/matrix.md` — add a "Per-framework reference"
   subsection and a row to the compatibility matrix. Put the `==X.Y.Z` pin in
   the per-framework `pip install` snippet here.
4. `skills/observent/references/examples.md` — add ≥1 runnable example (rotate
   which backend it targets) with a `*Last verified: <today> with Python X.Y.*`
   footer.
5. `skills/observent/references/matrix.md` § Verified Versions — add a row for
   the framework + instrumentor packages with the exact `==X.Y.Z` pin (same as
   step 3), and bump the table's "Last verified" date to today.
6. `tests/test_docs_consistency.py` — add the framework to `FRAMEWORKS`.

## Add a Backend

Edit in this order, diff-previewing each:

1. `skills/observent/scripts/validate_setup.py` — add `check_<backend>()`,
   register it in `CHECKS`, and add the backend to `BACKEND_CONVENTION`
   (`oi` for OpenInference-native, `otel-genai` otherwise).
2. `skills/observent/scripts/detect_framework.py` — add an entry to `BACKENDS`.
3. `skills/observent/SKILL.md` — update the description, the Phase 1 §1.3
   backend-options list, the convention-derivation table (if applicable), and
   the Phase 2 §2.5 endpoints table.
4. `skills/observent/references/matrix.md` — add a "Per-backend reference"
   subsection and a column to the matrix. Put the `==X.Y.Z` pin in the
   per-backend Install line here.
5. `skills/observent/references/examples.md` — add ≥1 example using the new
   backend with a `*Last verified: <today> with Python X.Y.*` footer.
6. `skills/observent/references/matrix.md` § Verified Versions — add a row with
   the exact `==X.Y.Z` pin (same as step 4) and bump "Last verified" to today.
7. **If self-hostable:** `skills/observent/references/self_host.md` — add a
   provisioning section (`vendored-compose` for a self-contained stack, or
   `upstream-clone` when it needs repo-mounted config), add a row to § Image
   Versions with exact image tag(s), bump that table's "Last verified", and add
   the backend to the provisionable set in `SKILL.md` Phase 1 §1.5. If it has
   **no** free self-host edition (like LangSmith), document it under the "not
   provisioned" note instead and leave it out of the set.
8. `tests/test_docs_consistency.py` — extend `BACKEND_COLUMNS`.

## Step N — Verify

Run the gates and report results plainly:

```bash
python -m pytest
ruff check skills/observent/scripts/ scripts/ tests/
mypy skills/observent/scripts/ scripts/
```

The PostToolUse hooks will have surfaced grid/pin drift as you edited, but run
the full suite to confirm. If anything is red, fix the doc or code so the grid
and pins agree (CLAUDE.md > Documentation Hygiene) before considering it done.
Optionally hand the diff to the `docs-hygiene-reviewer` subagent for a final
mirror-location audit.
