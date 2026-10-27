#!/usr/bin/env bash
# commit_msg_guard.sh — enforce the commit-message SUBSTANCE law
# (taught by the agent-team prompt templates + the turn-step brief —
# Owner 2026-10-27 #hq: "This rule doesn't belong to AGENTS.md, but your
# AGENT-TEAM prompt templates"; this guard is enforcement, not the source):
# subjects must describe what changed; mechanical turn metadata is banned.
#
# Owner order 2026-10-27 (#hq): commit messages are written by agents
# about what changed in the code — never "ci turn", "stall", etc.
#
# Usage: commit_msg_guard.sh <git-range>
#   e.g. commit_msg_guard.sh origin/ai/main..HEAD
#
# Exit 0 = every subject in the range passes.
# Exit 1 = violations printed (sha + subject + reason).
#
# Rules:
#   1. Subject carries >= 3 words.
#   2. Subject does not START with turn-metadata labels:
#      ci-turn / ci-chain / ci turn / ci chain / turn( / wip / progress /
#      misc / various / done / temp / tmp / changes / commit / stall=N.
set -u

RANGE="${1:?usage: commit_msg_guard.sh <git-range>}"

BANNED_RE='^(ci[-_ ]?(turn|chain)|turn\(|wip\b|progress\b|misc\b|various\b|done\b|temp\b|tmp\b|changes\b|commit\b|stall=[0-9])'

fail=0
count=0
# An unresolvable range must FAIL LOUDLY, never pass silently: a gate
# that cannot read the history must not wave it through.
LOG=$(git log --format='%h %s' "$RANGE" 2>/tmp/cmg-err.txt)
if [ $? -ne 0 ]; then
  echo "commit-msg guard: BAD RANGE '${RANGE}' — $(head -1 /tmp/cmg-err.txt)"
  rm -f /tmp/cmg-err.txt
  exit 2
fi
rm -f /tmp/cmg-err.txt
while IFS= read -r line; do
  [ -n "$line" ] || continue
  sha=${line%% *}
  subj=${line#* }
  count=$((count + 1))
  reasons=""
  words=$(printf '%s' "$subj" | wc -w)
  if [ "$words" -lt 3 ]; then
    reasons="${reasons}subject has <3 words; "
  fi
  if printf '%s' "$subj" | grep -qiE "$BANNED_RE"; then
    reasons="${reasons}mechanical/turn-metadata subject; "
  fi
  if [ -n "$reasons" ]; then
    echo "VIOLATION ${sha}: ${subj}"
    echo "  -> ${reasons}"
    echo "     law: subjects name WHAT changed (file/feature/behavior + effect)"
    fail=1
  fi
done <<< "$LOG"

if [ "$fail" = 0 ]; then
  echo "commit-msg guard: ${count} commit(s) in ${RANGE} all describe their changes"
else
  echo "commit-msg guard: FAIL — ${RANGE} carries mechanical subjects (see above)"
fi
exit $fail
