# agent-team-ci integration contract (every agent-team repo)

Owner order 2026-10-27 (#hq): the CI kit is a SUBMODULE every repo uses,
ALL Docker agents read BOTH laws, and the global law lives in this
submodule. Adopting repos follow this contract.

## 1. Install

```bash
git submodule add https://github.com/khaalidrafi/agent-team-ci.git ci
git commit -m "ci: adopt agent-team-ci submodule (shared harness + dual-law kit)"
```

CI checkouts MUST include the submodule:

```yaml
- uses: actions/checkout@v4
  with:
    submodules: recursive
```

## 2. Harness image

Build the canonical harness from YOUR repo root (context = repo root, so
the Dockerfile can bake `ci/AGENTS.md` — the global law — into every
body's rules slot):

```yaml
- uses: docker/build-push-action@v6
  with:
    context: .
    file: ci/docker/harness/Dockerfile
```

Project-specific bodies (baked node_modules, python venvs, ...) extend
the canonical image — write `FROM <your-team-harness>` in a thin local
Dockerfile and keep the body installs + law bakes inherited, never
forked. If you must diverge, port the change upstream to agent-team-ci first;
a local fork without an upstream PR is a compliance violation.

## 3. Dual-law brief (THE mechanism — no agent runs lawless)

Every lane composes its prompt through `ci/bin/law_brief.sh`:

```bash
printf '%s\n' "$SEGMENT_BRIEF" > /tmp/segment-brief.txt
BRIEF="$(bash ci/bin/law_brief.sh /tmp/segment-brief.txt "$PWD")"
# hand $BRIEF to the agent body (env, argv, or file — body's contract)
```

Output = GLOBAL LAW (ci/AGENTS.md) + LOCAL LAW (repo root AGENTS.md) +
SEGMENT BRIEF. Missing files produce loud MISSING markers, never silent
lawless runs. Budget-limited lanes may set `CI_LAW_DIGEST` to a
COMMITTED condensed digest of the local law — never an improvised one.

Raw-curl lanes (no agent body) prepend the same composed brief to the
messages array.

## 4. Commit-message guard

Land nothing with mechanical subjects. In your finalize/gate job:

```bash
bash ci/bin/commit_msg_guard.sh "${BASE_SHA}..HEAD" \
  || { git reset --hard origin/main; echo "gate=red-commit-msg"; }
```

Subjects must name WHAT changed (>= 3 words); banned openers: `ci-turn`,
`ci-chain`, `turn(...)`, `wip`, `progress`, `misc`, `done`, `stall=N`,
bare `update`/`fix`. State-file commits stay compliant by naming the
field that moved (e.g. `control: rotate #+TURN to <seat> after <seat>
segment`).

## 5. Commit generators

Fix every automated `git commit` in your workflows to produce
descriptive subjects per the global law. Agents write their OWN commit
messages describing their change — the brief must say so.

## 6. Verification duty (first migration turn)

Report in your TEAM-CHAT, with evidence:
- lane x global-law x local-law x mechanism matrix (which lane, which
  file, what carried it, request-id/token proof where the body allows),
- per-category violation counts (path x law clause x severity) for the
  whole-repo compliance audit, each with fix commit or BLOCKED,
- confirmation that `ci/bin/commit_msg_guard.sh` gates your merge.
