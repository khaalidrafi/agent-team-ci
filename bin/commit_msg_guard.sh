#!/usr/bin/env bash
# commit_msg_guard.sh — enforce the commit-message SUBSTANCE law
# (taught by the agent-team prompt templates + the turn-step brief —
# Owner 2026-10-27 #hq: "This rule doesn't belong to AGENTS.md, but your
# AGENT-TEAM prompt templates"; this guard is enforcement, not the source):
# subjects must describe what changed; mechanical turn metadata is banned.
#
# Owner order 2026-10-27 (#hq): commit messages are written by agents
# about what changed in the code — never "ci turn", "stall", etc.
# Owner order 2026-10-29 (#hq): changes made by agents on CI MUST be
# committed by that agent's author, not the model that ran CI — a
# `turn(<seat>):` commit authored by the CI bot identity is a violation.
#
# Owner order 2026-11-07 #hq ("teams keep missing global instructions"):
# the 2026-11-07 audit showed the misses were NOT subject problems — they
# were identity + trailer problems in lanes that never booted from a kit
# prompt (lead-side container sessions, "Z User <z@container>",
# "Lead Desk <lead@...>", harness-name authors, and ~100+ commits with
# zero Co-authored-by trailers). So the guard now enforces the global
# AGENTS.md commit law on EVERY commit in the range, not only turn(*) ones:
#   4. BOTH trailers present: `Co-authored-by: <agent/harness>` AND
#      `Co-authored-by: Khalid Rafi <khaalidrafi@gmail.com>` — the
#      canonical gmail, no variants (no noreply, no other emails).
#   5. Author is a model identity MODEL <MODEL@PROVIDER>: well-formed
#      name <user@host.tld>, never a role/machine/harness name
#      (unknown, Z User, Lead Desk, agent-team-ci, z.ai-agent, ...).
#   Exception: commits authored by Khalid himself (khaalidrafi@gmail.com)
#   are the human's own work — rules 4/5 do not apply to them.
#
# Usage: commit_msg_guard.sh <git-range>
#   e.g. commit_msg_guard.sh origin/ai/main..HEAD
#
# Exit 0 = every commit in the range passes.
# Exit 1 = violations printed (sha + subject + reason).
# Exit 2 = the range itself could not be read (never pass silently).
#
# Rules:
#   1. Subject carries >= 3 words.
#   2. Subject does not START with turn-metadata labels:
#      ci-turn / ci-chain / ci turn / ci chain / wip / progress /
#      misc / various / done / temp / tmp / changes / commit / stall=N.
#      (`turn(<seat>):` is the harness's RESERVED host-commit prefix —
#      governed by rule 3, not banned outright.)
#   3. A `turn(<seat>):` subject (host-committed agent work) must carry
#      the AGENT as git author in the AGENTS.md model format
#      MODEL <MODEL@PROVIDER> — never agent-team-ci@users.noreply,
#      never a raw lane string ("model@provider") as the NAME,
#      never "unknown" (Owner correction 2026-10-30 #hq).
#   4. Every agent commit carries BOTH co-author trailers (see above).
#   5. Every agent commit's author is a model identity (see above).
set -u

RANGE="${1:?usage: commit_msg_guard.sh <git-range>}"

BANNED_RE='^(ci[-_ ]?(turn|chain)|wip\b|progress\b|misc\b|various\b|done\b|temp\b|tmp\b|changes\b|commit\b|stall=[0-9])'
CI_MACHINE_RE='agent-team-ci@users\.noreply\.github\.com'
# Rule 5: names that are roles/machines/harnesses, never models
# (each of these was actually observed in the 2026-11-07 audit).
NONMODEL_NAME_RE='^(unknown|z user|lead desk|lead-desk|agent-team-ci|z\.ai-agent)$'
OWNER_EMAIL='khaalidrafi@gmail.com'
KHALID_TRAILER_RE='^co-authored-by: Khalid Rafi <khaalidrafi@gmail\.com>[[:space:]]*$'

fail=0
count=0
# An unresolvable range must FAIL LOUDLY, never pass silently: a gate
# that cannot read the history must not wave it through.
# Records are RS-separated (\x1e) so multi-line commit bodies travel
# inside one record; fields are tab-separated:
#   sha \t author-name \t author-email \t subject \t body
LOG=$(git log --format='%h%x09%an%x09%ae%x09%s%x09%b%x1e' "$RANGE" 2>/tmp/cmg-err.txt)
if [ $? -ne 0 ]; then
  echo "commit-msg guard: BAD RANGE '${RANGE}' — $(head -1 /tmp/cmg-err.txt)"
  rm -f /tmp/cmg-err.txt
  exit 2
fi
rm -f /tmp/cmg-err.txt
while IFS= read -rd $'\x1e' record; do
  [ -n "$record" ] || continue
  # Split ONLY the 4 leading tab fields by parameter expansion — `read`
  # stops at the first NEWLINE and would drop every body line after the
  # first, i.e. both Co-authored-by trailers of any multi-line body
  # (found live 2026-11-08: the guard false-FAILed its own author).
  sha=${record%%$'\t'*};      rest=${record#*$'\t'}
  an=${rest%%$'\t'*};         rest=${rest#*$'\t'}
  ae=${rest%%$'\t'*};         rest=${rest#*$'\t'}
  subj=${rest%%$'\t'*}
  body=${rest#*$'\t'}
  [ -n "$sha" ] || continue
  count=$((count + 1))
  reasons=""
  words=$(printf '%s' "$subj" | wc -w)
  if [ "$words" -lt 3 ]; then
    reasons="${reasons}subject has <3 words; "
  fi
  # Rule 6 (Owner 2026-11-08 #hq): "Keep them simple, concise and
  # straightforward! Description goes to the line after commit message!
  # Having ONE BIG LINE trying to say it ALL is CRAP!" The subject NAMES
  # the change; the description lives in the body. Subject cap = 72
  # chars, matching the git log --oneline convention and the seat
  # prompt's "subject <= 72 chars" law.
  if [ "$(printf '%s' "$subj" | wc -c)" -gt 72 ]; then
    reasons="${reasons}subject is $(( $(printf '%s' "$subj" | wc -c) )) chars (>72) — keep the subject short, put the description in the body; "
  fi
  if printf '%s' "$subj" | grep -qiE "$BANNED_RE"; then
    reasons="${reasons}mechanical/turn-metadata subject; "
  fi
  # Owner law 2026-10-29: agent work carries the agent's author.
  # Owner correction 2026-10-30: that author is a MODEL identity in the
  # AGENTS.md format MODEL <MODEL@PROVIDER> (e.g.
  # "Qwen3.8-Flash <qwen3.8-flash@qoder.com>") — never the CI machine,
  # never a raw lane string as the name, never "unknown".
  case "$subj" in
    turn\(*)
      if printf '%s' "$ae" | grep -qE "$CI_MACHINE_RE"; then
        reasons="${reasons}agent work authored by the CI machine (law: turn work carries the agent's author); "
      fi
      if printf '%s' "$an" | grep -qE '^[^<]*@[^<]*<'; then
        reasons="${reasons}author name is a lane string, not a model name (law: MODEL <MODEL@PROVIDER>); "
      fi
      ;;
  esac
  # Owner order 2026-10-31 #hq: control subjects describe their change in
  # plain words — "unknown" means the writer did not know what ran, which
  # is exactly the spam the Owner rejected.
  case "$subj" in
    control:*|ci-turn:*|ci-chain:*)
      if printf '%s' "$subj" | grep -qiE '(^|[ :])unknown([ ,.;!]|$)'; then
        reasons="${reasons}control subject says 'unknown' (law: name the lane/seat); "
      fi
      ;;
  esac
  # Rules 4+5 (Owner 2026-11-07 #hq): global commit law on EVERY commit.
  # Khalid's own commits are the human's work — outside this gate.
  if [ "$ae" != "$OWNER_EMAIL" ]; then
    if ! printf '%s\n' "$body" | grep -qiE "$KHALID_TRAILER_RE"; then
      reasons="${reasons}missing trailer 'Co-authored-by: Khalid Rafi <khaalidrafi@gmail.com>' (canonical email, no variants); "
    fi
    trailers=$(printf '%s\n' "$body" | grep -icE '^co-authored-by:' || true)
    if [ "${trailers:-0}" -lt 2 ]; then
      reasons="${reasons}needs BOTH trailers (agent/harness + owner), found ${trailers:-0}; "
    fi
    if printf '%s' "$an" | grep -qiE "$NONMODEL_NAME_RE"; then
      reasons="${reasons}author is a role/machine/harness name, not a model (law: MODEL <MODEL@PROVIDER>); "
    fi
    if ! printf '%s' "$ae" | grep -qE '^[^ <>,]+@[^ <>,]+\.[A-Za-z]{2,}$'; then
      reasons="${reasons}author email malformed (law: MODEL <MODEL@PROVIDER>); "
    fi
    if printf '%s' "$ae" | grep -qE "$CI_MACHINE_RE"; then
      reasons="${reasons}author is the CI machine identity; "
    fi
  fi
  if [ -n "$reasons" ]; then
    echo "VIOLATION ${sha}: ${subj}"
    echo "  -> author: ${an} <${ae}>"
    echo "  -> ${reasons}"
    echo "     law: subjects name WHAT changed; author = MODEL <MODEL@PROVIDER>; BOTH trailers (harness + Khalid Rafi <khaalidrafi@gmail.com>)"
    fail=1
  fi
done <<< "$LOG"

if [ "$fail" = 0 ]; then
  echo "commit-msg guard: ${count} commit(s) in ${RANGE} all pass (subject + identity + trailers)"
else
  echo "commit-msg guard: FAIL — ${RANGE} carries violations (see above)"
fi
exit $fail
