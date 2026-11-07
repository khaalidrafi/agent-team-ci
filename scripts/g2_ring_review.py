#!/usr/bin/env python3
"""G2 ring-lane code review — pooled intern model via the intern harness.

All model requests ride the Owner-ordered lane (docs/INTERN-ELISP.org):
reviews call intern_elisp.ask(), never ad-hoc HTTP from elsewhere.
The reviewer sees the full source + the certification facts and must
answer with a verdict line `VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES`
plus concrete findings.

Usage:
  g2_ring_review.py PROMPT_FILE OUT_FILE [MODEL]
Defaults to the pooled free model (INTERN-ELISP.org 2026-11-07:
xingchen-agi/xing4.0-29b-a4b:free, the only cohort member with real cards).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intern_elisp import ask

DEFAULT_MODEL = "xingchen-agi/xing4.0-29b-a4b:free"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    prompt_file, out_file = sys.argv[1], sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL
    maxtok = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
    prompt = open(prompt_file).read()
    content, reasoning, cost = ask(model, prompt, maxtok=maxtok)
    text = (content or "").strip() or (reasoning or "").strip()
    if not text:
        # ask() surfaces honest ERR rows — never fabricate a verdict.
        print("RING-REVIEW: BLOCKED (%s)" % (reasoning or "empty reply"))
        sys.exit(1)
    open(out_file, "w").write(text)
    print("model=%s cost=%s bytes=%d" % (model, cost, len(text)))
    print(text[:600])


if __name__ == "__main__":
    main()
