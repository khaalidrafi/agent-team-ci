#!/usr/bin/env python3
"""cf_repo_audit.py — static Cloudflare security audit for a repo tree.

Reads wrangler.{json,jsonc,toml}, .dev.vars, _headers, static site dirs and
GitHub workflows; prints findings as `SEVERITY path:line — finding — fix`.
Exit 1 when CRITICAL or HIGH findings exist. No network, no tokens.

Usage: cf_repo_audit.py [repo-root]  (default: .)
"""
import json
import os
import re
import sys
from datetime import date, datetime

SECRET_NAME = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|PAT)\b", re.I)
TOKEN_LIKE = re.compile(r"\b[A-Za-z0-9_-]{32,}\b")
CF_TOKEN_ASSIGN = re.compile(r"(?:CF|CLOUDFLARE)[_A-Z]*API[_A-Z]*TOKEN\s*[:=]\s*[\"']?[A-Za-z0-9_-]{20,}", re.I)
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "site-corpus",
             ".svelte-kit", "build", "forge-out-kimi", "bench", "dist"}
STATIC_DIRS = ("public", "dist", "static", "out", "build")
VAR_BLOCKS = ("vars", "[vars]")

def is_tokenish(s):
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{32,}", s)) and re.search(r"[A-Za-z]", s) and re.search(r"[0-9]", s)

def strip_jsonc(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)

def walk(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            out.append(os.path.join(dirpath, f))
            if len(out) > 8000:
                return out
    return out

def rel(root, p):
    return os.path.relpath(p, root)

def scan_wrangler(root, path):
    find = []
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    is_toml = path.endswith(".toml")
    data = None
    if is_toml:
        try:
            import tomllib
            data = tomllib.loads(text)
        except Exception:
            data = None
    else:
        try:
            data = json.loads(strip_jsonc(text))
        except Exception:
            data = None
    # plaintext secrets in vars
    if isinstance(data, dict):
        v = data.get("vars")
        if isinstance(v, dict):
            for k, val in v.items():
                if SECRET_NAME.search(str(k)):
                    line = next((i + 1 for i, l in enumerate(lines) if k in l), 1)
                    find.append(("HIGH", f"{rel(root, path)}:{line} — plaintext secret-shaped var '{k}' in wrangler vars — move to `wrangler secret put` / repo secrets, never vars"))
                elif isinstance(val, str) and is_tokenish(val):
                    find.append(("CRITICAL", f"{rel(root, path)}:{k} — token-shaped literal in var '{k}' — rotate the secret NOW, move to repo secrets"))
    elif is_toml and data is None:
        in_vars = False
        for i, l in enumerate(lines):
            s = l.strip()
            if s == "[vars]":
                in_vars = True
                continue
            if s.startswith("[") and s != "[vars]":
                in_vars = False
            if in_vars and SECRET_NAME.search(s):
                find.append(("HIGH", f"{rel(root, path)}:{i+1} — secret-shaped name in plaintext [vars] — move to `wrangler secret put` / repo secrets"))
    # token-shaped literals anywhere in the config
    for i, l in enumerate(lines):
        if CF_TOKEN_ASSIGN.search(l):
            find.append(("CRITICAL", f"{rel(root, path)}:{i+1} — literal Cloudflare API token assignment — rotate NOW, use repo secrets + " + "${{ secrets.CLOUDFLARE_API_TOKEN }}"))
        elif is_tokenish(l) and SECRET_NAME.search(l):
            find.append(("HIGH", f"{rel(root, path)}:{i+1} — token-shaped literal near a secret name — verify and move to repo secrets"))
    # compatibility_date staleness
    m = re.search(r"compatibility_date\s*[:=]\s*[\"']?(\d{4}-\d{2}-\d{2})", text)
    if m:
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            if (date.today() - d).days > 365:
                find.append(("LOW", f"{rel(root, path)}:{m.start()} — compatibility_date {m.group(1)} is >12 months old — bump it to pick up runtime security fixes"))
        except ValueError:
            pass
    # bindings inventory
    if isinstance(data, dict):
        inv = []
        for k in ("kv_namespaces", "r2_buckets", "d1_databases", "services", "durable_objects", "queues"):
            if data.get(k):
                inv.append(f"{k}={len(data[k]) if isinstance(data[k], list) else 1}")
        if data.get("nodejs_compat") or "nodejs_compat" in text:
            inv.append("nodejs_compat=on")
        if inv:
            find.append(("INFO", f"{rel(root, path)}:1 — bindings: {', '.join(inv)} — reviewer checks each binding is scope-minimal"))
        for k in ("routes", "route", "custom_domains"):
            if data.get(k):
                find.append(("INFO", f"{rel(root, path)}:1 — {k} present: {data.get(k)} — reviewer confirms routes are intentional"))
    return find

def scan_tree(root):
    find = []
    files = walk(root)
    wranglers = [p for p in files if os.path.basename(p).startswith("wrangler.") and os.path.basename(p) in ("wrangler.json", "wrangler.jsonc", "wrangler.toml")]
    for w in wranglers:
        find.extend(scan_wrangler(root, w))
    # committed .dev.vars
    for p in files:
        if os.path.basename(p) == ".dev.vars":
            find.append(("HIGH", f"{rel(root, p)}:1 — .dev.vars committed to the tree — gitignore it; rotate any value inside NOW"))
    # static site dir without _headers
    has_headers = any(os.path.basename(p) == "_headers" for p in files)
    if not has_headers:
        for p in files:
            d = os.path.basename(os.path.dirname(p))
            if d in STATIC_DIRS and os.path.basename(p) in ("index.html", "404.html", "robots.txt"):
                find.append(("MEDIUM", f"{rel(root, os.path.dirname(p))}/ — static site dir without _headers — add CSP + HSTS via a _headers file (Pages) or the Worker's response headers"))
                break
    # token-shaped literals in workflows and scripts
    for p in files:
        b = os.path.basename(p)
        if b.startswith("wrangler."):
            continue
        if b.endswith((".yml", ".yaml", ".sh", ".py", ".mjs", ".js", ".ts")):
            try:
                lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            for i, l in enumerate(lines):
                if "secrets." in l or "${{ github.event" in l:
                    continue
                if CF_TOKEN_ASSIGN.search(l):
                    find.append(("CRITICAL", f"{rel(root, p)}:{i+1} — literal Cloudflare API token assignment — rotate NOW, use " + "${{ secrets.CLOUDFLARE_API_TOKEN }}"))
    return find

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(root):
        print(f"ERROR — not a directory: {root}")
        return 2
    find = scan_tree(root)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    find.sort(key=lambda x: order[x[0]])
    if not find:
        print("CLEAN — no Cloudflare findings")
        return 0
    for sev, msg in find:
        print(f"{sev} — {msg}")
    bad = any(sev in ("CRITICAL", "HIGH") for sev, _ in find)
    print(f"\nSUMMARY — " + ", ".join(f"{s}:{sum(1 for x, _ in find if x == s)}" for s in order if any(x == s for x, _ in find)))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
