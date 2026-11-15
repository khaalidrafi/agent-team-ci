---
name: cloudflare-security-audit
description: Static security audit of a repo's Cloudflare surface (Workers/Pages/wrangler configs, headers, secret hygiene) before a deploy. No Cloudflare API access, no tokens — everything is read from the tree itself.
---

# Cloudflare Security Audit

Run this skill before any Cloudflare deploy (Workers, Pages, `wrangler deploy`,
`wrangler pages deploy`) and whenever a wrangler config, `.dev.vars`, `_headers`,
or a deploy workflow changes. Everything is STATIC — the scanner reads the repo
tree only. It never calls the Cloudflare API and never needs a token (secret
law: keys live in vault/repo secrets, never in scans).

## When to use

- a wrangler.{json,jsonc,toml} file was added or changed,
- a deploy workflow (.github/workflows/*) touching Cloudflare changed,
- a site ships `_headers`, `_redirects`, or public/static dirs,
- the Owner asks for a security pass on a Cloudflare-hosted repo.

## How to run

```bash
python3 skills/cloudflare-security-audit/scripts/cf_repo_audit.py <repo-root>
# inside the harness the pack is baked at /opt/agent-team-ci-skills:
python3 /opt/agent-team-ci-skills/cloudflare-security-audit/scripts/cf_repo_audit.py .
```

Exit code 1 = CRITICAL or HIGH findings present — fix before deploying.
Exit code 0 = clean or LOW/INFO only (report them anyway).

## What it flags

- CRITICAL — a Cloudflare-token-shaped literal (32+ chars, token charset) in a
  config, workflow, or script: a real secret committed to the tree.
- HIGH — secret-looking NAME (matches TOKEN|KEY|SECRET|PASSWORD|PAT) assigned a
  plaintext value in `vars` / `[vars]` (must be a `wrangler secret` / repo
  secret instead); `.dev.vars` committed to the tree.
- MEDIUM — a static site dir (public/, dist/, static/, out/, build/) with no
  `_headers` file: CSP and HSTS unset.
- LOW — `compatibility_date` more than 12 months behind (missed security
  fixes in the runtime).
- INFO — bindings inventory (KV / R2 / D1 / services / durable objects),
  routes and custom domains, `nodejs_compat` flag: recorded so a reviewer can
  spot over-scoped bindings.

## Report format

Findings print one per line: `SEVERITY path:line — finding — fix`.
Finish the audit by listing every finding in the delivery note with its fix
(or "accepted" + reason). CRITICAL/HIGH findings block the deploy — fix commits
land first.

## Limits (read before trusting)

- Static only: it cannot see your Cloudflare account (WAF rules, DNS, zone
  settings, token scopes). Those stay Owner-side checks.
- Token detection is heuristic — a clean run is not proof no secret leaked;
  it never replaces `git log` review after a leak.
