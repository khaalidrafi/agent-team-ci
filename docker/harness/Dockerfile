# agent-harness-base (canonical, khaalidrafi/agent-team-ci) — CI turn container
# with agent bodies PREINSTALLED.
# Owner order 2026-10-20 (#hq): "Use Docker containers with agents
# preinstalled. Don't install in CI. That's a waste of time. You'll have
# to make agent configs, too, and reuse them."
# Owner order 2026-10-27 (#hq): this Dockerfile lives in the agent-team-ci
# SUBMODULE every agent-team repo consumes at ci/. Build it from the
# CONSUMING REPO'S ROOT as build context:
#   docker buildx build -f ci/docker/harness/Dockerfile -t <team-harness> .
# DUAL-LAW ARCHITECTURE (Owner order 2026-10-27 #hq):
#   GLOBAL law  = ci/AGENTS.md (this submodule) — baked into every body's
#                 global/user rules slot below; present in every repo, and
#                 the submodule pointer pins the law version per commit.
#   LOCAL law   = the consuming repo's own root AGENTS.md — NOT baked
#                 (optional file): bodies auto-read it from CWD. The
#                 brief prepend is OPTIONAL (Owner 2026-10-27 #hq: no
#                 need to prepend with law_brief.sh) — the bake above
#                 is the delivery mechanism. No agent ever runs lawless.
# Secrets are NEVER baked: provider keys are injected per run as env vars
# (OPENROUTER_API_KEY / ZAI_API_KEY / GROQ_API_KEY /
#  QODER_PERSONAL_ACCESS_TOKEN / CODEBUDDY_*) from repo secrets.
# Project harnesses (extra deps: node modules, python venvs) extend this
# image: FROM <this image> + your project layers — see templates/.

FROM debian:stable-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git curl ca-certificates bzip2 jq procps \
 && rm -rf /var/lib/apt/lists/*

# --- Node 22 (Owner order 2026-10-27 #hq fleet: pi needs Node >= 22.19,
#     mcode needs 22.19+/24-26; debian stable ships an older nodejs) -------
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# --- OpenCode body (preinstalled once, reused every turn) -------------------
# Installed under /usr/local/lib so the non-root run user can traverse it.
RUN export HOME=/usr/local/lib/opencode-home \
 && curl -fsSL https://opencode.ai/install | bash \
 && chmod -R a+rX /usr/local/lib/opencode-home \
 && ln -sf /usr/local/lib/opencode-home/.opencode/bin/opencode /usr/local/bin/opencode

# --- Goose body (direct tarball: the download_cli.sh installer opens
#     /dev/tty and dies on headless runners — demo/01 turn 2 evidence) ------
RUN mkdir -p /tmp/goose-dl \
 && curl -fsSL --retry 5 --retry-all-errors --retry-delay 5 -m 300 -o /tmp/goose-dl/goose.tar.bz2 \
      https://github.com/block/goose/releases/download/stable/goose-x86_64-unknown-linux-gnu.tar.bz2 \
 && test -s /tmp/goose-dl/goose.tar.bz2 && tar -xjf /tmp/goose-dl/goose.tar.bz2 -C /tmp/goose-dl \
 && install -m 0755 /tmp/goose-dl/goose /usr/local/bin/goose \
 && rm -rf /tmp/goose-dl

# --- Qoder body (keys landed 2026-10-21: Owner PAT -> repo secret
#     QODER_PERSONAL_ACCESS_TOKEN; CLI auto-detects CI and uses the PAT,
#     no browser — Task 6 auth research).
#     RUNTIME ROOT CAUSE (proof run 39467719908, first platform segment):
#     the installer's `qoder` launcher resolves the real CLI under ITS
#     HOME — at build (HOME=/usr/local/lib/qoder-home) the version check
#     passed, at segment runtime HOME=/home/agent it printed "Qoder CLI
#     is not installed". Fix: keep the install tree under a+rwx and run
#     the launcher with HOME pinned to the install dir (also done in
#     ci.yml's platform branch). Version check is FATAL now — a body that
#     cannot run must fail the build loudly, not hide behind || true.
#     PATH FIX (CI evidence 2026-10-21, runs 39470194454/39470807232): the
#     installer does NOT put the dispatcher on PATH at all — it lives at
#     $HOME/.qoder/entry/qoder and resolves the real CLI via
#     $HOME/.local/bin/qodercli. Symlink the entry into /usr/local/bin at
#     build; HOME stays pinned (build here, runtime in ci.yml) so the
#     dispatcher's $HOME-relative discovery works for uid 1001. ---
RUN export HOME=/usr/local/lib/qoder-home \
 && curl -fsSL https://qoder.com/install | bash \
 && chmod -R a+rwX /usr/local/lib/qoder-home \
 && ln -sf /usr/local/lib/qoder-home/.qoder/entry/qoder /usr/local/bin/qoder \
 && timeout 60 qoder --version

# --- CodeBuddy body (Owner law 2026-10-21 17:47Z: CodeBuddy is kept for
#     its BUILT-IN models only. For API-served brains there is no novelty
#     in any body — "any agent can ride APIs, no surprise" — so the model
#     brain is installed into the BODY THAT FITS the work instead. Baked
#     and DORMANT until a CodeBuddy account credential exists (access
#     keys are pro-only; CODEBUDDY_AUTH_TOKEN / CODEBUDDY_API_KEY envs
#     ready to wire the moment one lands). Headless needs -y in -p mode
#     for tool use.) ----------------------------------------------------
RUN npm install -g @tencent-ai/codebuddy-code \
 && timeout 60 codebuddy --version

# --- pi body (earendil-works/pi 1.4.x — "a minimal, extensible agent
#     harness that you can make your own"; Owner order 2026-10-27 #hq:
#     look into its configs and customize it for agent-team usage).
#     CUSTOMIZED: the global law is baked into ~/.pi/agent/AGENTS.md —
#     pi's own docs (docs/configuration.md, read 2026-10-27): the agent
#     directory ~/.pi/agent holds AGENTS.md as "user instructions applied
#     across working directories". Headless: `pi --print`, `--mode json`.
#     Brains: BYOK via env vars / auth.json — keys are env-injected per
#     run, NEVER baked. npm --ignore-scripts per upstream README. ---
RUN npm install -g --ignore-scripts @earendil-works/pi-coding-agent \
 && timeout 60 pi --version

# --- dsh body (DeepSeek Harness, @deepseek-ai/dsh 0.2.x — DEV PREVIEW,
#     breaking changes expected; Owner order 2026-10-27 #hq: add it).
#     Headless bundle: one-shot Agent/Session runner, no Host/HTTP —
#     CI-ready. Pure BYOK (DeepSeek key + anthropic/openai/moonshotai/zai
#     + custom OpenAI/Anthropic-compatible gateways): creds live in
#     $DSH_HOME/.credentials.yaml and are env-injected per run, NEVER
#     baked. The global law MAY ride ci/bin/law_brief.sh (optional
#     prepend) + project AGENTS.md; no global rules file is documented for dsh. ---
RUN npm install -g @deepseek-ai/dsh \
 && timeout 60 dsh --version

# --- mcode body (MiniMax Code CLI 0.7.x). Headless: `mcode exec`
#     (PROVEN 2026-10-22 end-to-end); TUI `mcode`; `mcode init .` writes
#     the project AGENTS.md (project law auto-read). AUTH: repo secret
#     MCODE_AUTH_JSON -> CI writes ~/.minimax/auth/prod/en/mcode-public/
#     auth.json + auth-state.json at run time (CI-seedable refresh grant,
#     no PKCE needed — CANDIDATES.org profile). ASK-FIRST BODY (Owner
#     order 2026-10-27 #hq): the M-Plan-Free quota is LIMITED — the Lead
#     asks the Owner BEFORE a lane burns mcode credit. ---
RUN npm install -g @minimax-ai/code \
 && timeout 60 mcode --version

# --- Cursor CLI body (Anysphere; Owner correction 2026-10-27 #hq:
#     "Cursor, Copilot also have CLI"). Install verified headless
#     2026-10-27 (cursor/2026.10.22); the launcher resolves its own dir
#     through symlinks, so a /usr/local/bin symlink is safe. Headless:
#     `agent -p "..."` (--output-format text|json|stream-json, --trust).
#     Auth: CURSOR_API_KEY env per run — NEVER baked. Law: Cursor reads
#     AGENTS.md at the project root/subdirs + .cursor/rules; its "User
#     Rules" are dashboard-only (no file path) so the GLOBAL law MAY
#     ride ci/bin/law_brief.sh (optional prepend). ASK-FIRST BODY: Cursor usage is
#     credit-limited — ask the Owner before a lane burns it. ---
RUN export HOME=/usr/local/lib/cursor-home \
 && curl -fsSL https://cursor.com/install | bash \
 && chmod -R a+rX /usr/local/lib/cursor-home \
 && ln -sf /usr/local/lib/cursor-home/.local/bin/agent /usr/local/bin/agent \
 && ln -sf /usr/local/lib/cursor-home/.local/bin/cursor-agent /usr/local/bin/cursor-agent \
 && timeout 60 agent --version

# --- GitHub Copilot CLI body (@github/copilot 1.0.x; Owner correction
#     2026-10-27 #hq: "Copilot also has CLI"). Installer verified
#     headless 2026-10-27 (PREFIX=/usr/local). Headless: `copilot -p
#     "..."` (--allow-tool / --allow-all-tools). Auth: GH_TOKEN or
#     GITHUB_TOKEN env (fine-grained PAT with the "Copilot Requests"
#     permission) — env-injected per run, NEVER baked. Custom
#     instructions: repo .github/copilot-instructions.md (+ AGENTS.md at
#     the project root); no VERIFIED user-level rules file for the CLI,
#     so the GLOBAL law MAY ride ci/bin/law_brief.sh (optional
#     prepend). ASK-FIRST BODY
#     (Owner 2026-10-27 #hq): EVERY prompt burns one premium request
#     from the monthly quota — ask the Owner before a lane uses it. ---
RUN curl -fsSL https://gh.io/copilot-install | PREFIX=/usr/local bash \
 && timeout 60 copilot --version

# --- OMP body (oh-my-pi, omp.sh — Owner roster TEAM.md MODELS/Local).
#     Owner order 2026-10-27 #hq: "where is OMP?" — it sat roster-only,
#     never baked. Binary install verified headless 2026-10-27: static
#     omp-linux-x64 (no dynamic deps), sha256-verified by the installer,
#     no bun needed (--binary mode). Version check is FATAL like the
#     other bodies. ---
RUN export HOME=/usr/local/lib/omp-home \
 && curl -fsSL https://omp.sh/install | sh -s -- --binary \
 && chmod -R a+rX /usr/local/lib/omp-home \
 && ln -sf /usr/local/lib/omp-home/.local/bin/omp /usr/local/bin/omp \
 && timeout 60 omp --version

# --- Non-root run user (matches the Actions runner uid 1001) ---------------
RUN useradd -m -u 1001 agent

# --- Baked agent configs (Owner: "make agent configs, too, and reuse them").
#     Keys are env-interpolated at run time; nothing secret is baked. -------
COPY ci/docker/harness/opencode.json     /home/agent/.config/opencode/opencode.json
COPY ci/docker/harness/goose-config.yaml /home/agent/.config/goose/config.yaml
# Global AGENTS.md = agent law, CONFIGURED into memory (Owner 2026-10-21
# 08:22Z "configure the agent to load global AGENTS.md"; 09:16Z "read docs
# for each agent for how they configure global AGENTS.md"). Verified against
# each agent's official docs on 2026-10-21:
#   OpenCode  ~/.config/opencode/AGENTS.md — "applied across all opencode
#             sessions" (opencode.ai/docs/rules); repo-root AGENTS.md also
#             rides instructions[] in opencode.json.
#   Goose     ~/.config/goose/.goosehints is the GLOBAL hints file (goose
#             config dir, ~/.config/goose/); repo-root AGENTS.md/.goosehints
#             are additionally read from CWD per session.
#   CodeBuddy ~/.codebuddy/CODEBUDDY.md is the USER-LEVEL memory file,
#             "takes effect in all projects" (CodeBuddy docs, .codebuddy
#             directory structure); repo-root AGENTS.md auto-loads when no
#             CODEBUDDY.md exists (documented backward compatibility).
#             (Qoder + OMP rows re-verified against docs 2026-10-27 —
#             docs.qoder.com/cli/memory.md, omp.sh/docs/context-files.)
#   Qoder     ~/.qoder/AGENTS.md is the USER-level static memory — "cross-
#             project general preferences and working habits for the current
#             user" (docs.qoder.com/cli/memory.md; re-read 2026-10-27 after
#             the Owner's correction — the earlier "not documented" claim
#             was wrong); project AGENTS.md/AGENTS.local.md/.qoder/rules
#             auto-discovered walking up to the .git boundary.
#   OMP       ~/.omp/agent/AGENTS.md is the user-wide general context file
#             and ~/.omp/agent/RULES.md the user-wide sticky always-apply
#             rules (omp.sh/docs/context-files, read 2026-10-27); project
#             AGENTS.md auto-discovered (agents-md provider walks up to the
#             repo root).
#   pi        ~/.pi/agent/AGENTS.md — "user instructions applied across
#             working directories" (docs/configuration.md, read
#             2026-10-27); project .pi/ + AGENTS.md context files
#             auto-discovered.
#   dsh /     NO verified global rules file (dsh is DEV PREVIEW; Cursor's
#   Cursor /  "User Rules" are dashboard-only; Copilot CLI documents only
#   Copilot / repo-level instructions; mcode reads the project AGENTS.md
#   mcode     written by `mcode init .`) — their GLOBAL law MAY ride
#             ci/bin/law_brief.sh (optional prepend), their LOCAL law is
#             the repo's root AGENTS.md. No invented paths.
COPY ci/AGENTS.md /home/agent/.config/opencode/AGENTS.md
COPY ci/AGENTS.md /home/agent/.config/goose/.goosehints
COPY ci/AGENTS.md /home/agent/.codebuddy/CODEBUDDY.md
COPY ci/AGENTS.md /home/agent/.qoder/AGENTS.md
COPY ci/AGENTS.md /home/agent/.omp/agent/AGENTS.md
COPY ci/AGENTS.md /home/agent/.omp/agent/RULES.md
COPY ci/AGENTS.md /home/agent/.pi/agent/AGENTS.md
RUN chown -R agent:agent /home/agent

ENV HOME=/home/agent \
    GOOSE_PROVIDER=openrouter \
    GOOSE_MODEL=nvidia/nemotron-3.5-lightning:free

# agent-team.el chat command (Owner order 2026-10-27 #hq: TEAM-CHAT.org
# is COMMAND-MAINTAINED — seats send chat via `team-chat', never by
# hand). Baked at a pinned agent-team.el commit; AGENT_TEAM_EL_SHA is
# bumped with the consuming repo's kit pointer bump.
ARG AGENT_TEAM_EL_SHA=e9e5a772d468f6ebd06da354abffd7f36dd9f679
RUN mkdir -p /opt/agent-team \
 && curl -fsSL "https://raw.githubusercontent.com/khaalidrafi/agent-team.el/${AGENT_TEAM_EL_SHA}/agent-team.el" \
      -o /opt/agent-team/agent-team.el
COPY ci/docker/harness/team-chat /usr/local/bin/team-chat
RUN chmod +x /usr/local/bin/team-chat

STOPSIGNAL SIGTERM
