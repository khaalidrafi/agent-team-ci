# HUMANS.md — agent-team-ci (the "kit")

A guide for humans navigating and developing this codebase. Written
2026-11-18 per the org-wide rule that every agent-developed repo
carries one.

## What this is

The shared CI kit consumed as a git submodule (`ci/`) by every
agent-team repo in the org. Two things live here and only here:

1. **The canonical global law** — `AGENTS.md` at the repo root is THE
   global AGENTS.md the Owner refers to. A consuming repo pins a law
   version by pinning its submodule pointer; law updates propagate as
   ordinary, reviewable pointer bumps.
2. **The canonical agent harness** — `docker/harness/Dockerfile`
   builds the image every agent body runs in, with the global law
   baked into each body's verified global/user rules slot (11 bodies:
   OpenCode, Goose, Qoder, CodeBuddy, OMP, pi, Copilot, Devin,
   Gemini, Cline, Kilo) and shared body configs.

Plus the skills pack (`skills/`) baked to
`/opt/agent-team-ci-skills` in the harness, and the guard scripts
that make repo-level CI honest.

## Mental model

A repo consumes the kit like this: `git submodule add .../agent-team-ci
ci`, then per `templates/INTEGRATION.md` the repo's CI builds the
harness FROM THE REPO ROOT (so the repo's own files mount in), bodies
read BOTH laws (global from here + the repo's local `AGENTS.md`), and
`bin/commit_msg_guard.sh` gates the repo's merge lane. The kit never
runs as a project by itself; its own `self-check.yml` only proves the
kit before anyone consumes it.

The law hierarchy, as enforced: global law (this repo's AGENTS.md) +
repo-local AGENTS.md, the stricter rule winning on conflict;
`CI_LAW_DIGEST` is sanctioned only as a committed, reviewed digest
for budget lanes.

## Code map

| Path | Role |
|---|---|
| `AGENTS.md` | The global law. Environment, build/test policy for the Owner's low-spec Guix box, code rules (identity law, HUMANS.md law, no-reinvention law, commit format), workflow, response rules. |
| `bin/law_brief.sh` | Dual-law brief composer. REQUIRED only for the three bodies with no baked global slot (dsh / Cursor / mcode); baked bodies need no prepend. |
| `bin/commit_msg_guard.sh` | Commit-substance gate: rejects metadata-only subjects ("ci turn", "stall=N", "turn(<seat>):", "wip"). |
| `bin/harness_run_build.sh` | Harness build entry point. |
| `docker/harness/Dockerfile` (+ `*.json|yaml`) | The canonical harness image; bodies preinstalled, laws baked/mounted, skills baked to `/opt/agent-team-ci-skills`. |
| `skills/` | cloudflare-security-audit, vulnerability-harness, typesafe-ai (Jev judgments), code-simplification, slave-agent-builder, pstack (vendored at pinned SHA). |
| `templates/INTEGRATION.md` | The adoption contract — read before wiring a repo to the kit. |
| `templates/TEAMIFY-COMMON*.org`, `TODOS-CRON-PROMPT.org` | Teamify / cron prompt templates. |
| `scripts/intern_elisp.py`, `docs/INTERN-ELISP.org`, `docs/MSG-PROTOCOL.org` | The Elisp intern bridge for harness messaging. |
| `scripts/g2_ring_review.py` | G2 ring review pass. |
| `.github/workflows/self-check.yml` | Proves the kit (law present, no secrets, guard works) before anyone consumes it. |

## Invariants and gotchas

- This repo's AGENTS.md is the SINGLE SOURCE of the global law. Never
  paste law text into consuming repos; bump the pin instead.
- No secret baking: keys ride env vars per run; nothing
  credential-shaped ever lands here (self-check enforces).
- Submodule pins are the versioning mechanism: after a kit history
  rewrite (it happened once, 2026-11-18 identity restore), pre-rewrite
  pins become unreachable ("not our ref") and every consumer needs a
  one-line re-pin to the restored tip.
- The commit-substance RULE is taught by the agent-team prompt
  templates; this kit only enforces it. Keep the teaching and the
  enforcement in their respective homes (Owner order 2026-10-27).
- `main` receives merges from `ai/main`; law work lands on `ai/main`
  first. The two branches share history via an explicit merge; they
  have no natural common ancestor (the kit history was rebuilt once).

## Developing

- Self-check runs on push (`self-check.yml`); run it via the Actions
  UI or `docker build -f docker/harness/Dockerfile .` locally.
- Law changes: edit `AGENTS.md` on `ai/main`, cite the Owner order
  that mandated them (see existing bullets for the format), merge to
  `main`, then expect consuming repos to advance their `ci` pins.
- Consumers upgrade with `git submodule update --remote ci` or a
  pinned sha — a one-line, reviewable commit.
