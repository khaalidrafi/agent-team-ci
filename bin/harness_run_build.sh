#!/usr/bin/env bash
# harness_run_build.sh — MODULAR harness build (Owner order 2026-10-30 #hq:
# "on each CI run, only agents needed by that run can be built/used").
#
# The kit Dockerfile is one shared `base` stage + one `body-<name>` stage
# per agent. This script builds ONLY the bodies a run names, then unions
# exactly those onto the base in a tiny overlay image — BuildKit skips
# every other body stage, and cached bodies cost ~nothing.
#
# usage:
#   harness_run_build.sh -b <BASE_TAG> -o <OUT_TAG> [-f <DOCKERFILE>] -- [BODY...]
#   no BODY names -> FULL harness (every body; the legacy/unknown-seat
#                    fail-safe path — never a silently incomplete image)
# Body names are validated against the Dockerfile's own `FROM base AS
# body-<name>` stages; ANY unknown name fails safe to the full build.
set -euo pipefail

DOCKERFILE=ci/docker/harness/Dockerfile
BASE_TAG=
OUT_TAG=
while [ $# -gt 0 ]; do
  case "$1" in
    -f) DOCKERFILE=$2; shift 2 ;;
    -b) BASE_TAG=$2; shift 2 ;;
    -o) OUT_TAG=$2; shift 2 ;;
    --) shift; break ;;
    *) echo "harness_run_build.sh: unknown arg '$1'" >&2; exit 2 ;;
  esac
done
BODIES=("$@")
[ -n "$BASE_TAG" ] || { echo "harness_run_build.sh: -b BASE_TAG required" >&2; exit 2; }
[ -n "$OUT_TAG" ] || { echo "harness_run_build.sh: -o OUT_TAG required" >&2; exit 2; }
[ -f "$DOCKERFILE" ] || { echo "harness_run_build.sh: no such Dockerfile: $DOCKERFILE" >&2; exit 2; }

build() {
  docker buildx build --load \
    --cache-from type=gha \
    --cache-to type=gha,mode=max \
    "$@"
}

# Bodies defined by the kit Dockerfile itself (single source of truth).
KNOWN=$(sed -nE 's/^FROM base AS body-([a-z0-9-]+)$/\1/p' "$DOCKERFILE" | sort | tr '\n' ' ')

if [ "${#BODIES[@]}" -eq 0 ]; then
  echo "harness: no body list given -> FULL harness build (all bodies: ${KNOWN:-?})"
  build -f "$DOCKERFILE" -t "$OUT_TAG" .
  exit 0
fi

BAD=""
for b in "${BODIES[@]}"; do
  case " $KNOWN " in
    *" $b "*) ;;
    *) BAD="$BAD $b" ;;
  esac
done
if [ -n "$BAD" ]; then
  echo "::warning::harness_run_build.sh: unknown body(s):$BAD — failing safe to the FULL harness build (known bodies: $KNOWN)"
  build -f "$DOCKERFILE" -t "$OUT_TAG" .
  exit 0
fi

echo "harness: MODULAR build — bodies:${BODIES[*]} (kit can also provide: $KNOWN)"
build -f "$DOCKERFILE" --target base -t "$BASE_TAG" .
for b in "${BODIES[@]}"; do
  echo "harness: building ONLY body-$b"
  build -f "$DOCKERFILE" --target "body-$b" -t "harness-body-$b:local" .
done

# Overlay: FROM base + one COPY per body (directory COPY merges, never
# deletes — base-owned files like /usr/local/bin/team-chat and
# /opt/agent-team survive; sibling-body files stay intact).
TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT
{
  echo "FROM $BASE_TAG"
  for b in "${BODIES[@]}"; do
    echo "COPY --from=harness-body-$b:local /usr/local /usr/local"
    echo "COPY --from=harness-body-$b:local --chown=1001:1001 /home/agent /home/agent"
  done
} > "$TMPD/Dockerfile"
echo "harness: overlaying ${#BODIES[@]} body image(s) onto the shared base -> $OUT_TAG"
build -f "$TMPD/Dockerfile" -t "$OUT_TAG" .
echo "harness: DONE — $OUT_TAG carries exactly:${BODIES[*]}"
