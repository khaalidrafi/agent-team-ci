#!/usr/bin/env python3
"""ELisp internship battery — OpenRouter models, static-scored.

The Lead's direct lane (docs/INTERN-ELISP.org): ALL internship model
requests go through this harness — never ad-hoc calls from elsewhere.
Usage:
  intern_elisp.py                 battery on the default cohort (Ling pair)
  intern_elisp.py MODEL [MODEL…]  battery on named candidates (slugs)
  intern_elisp.py --free-scan     list the newest OpenRouter zero-cost models
"""
import urllib.request, urllib.error, json, re, sys, time

KEY = open("/home/z/my-project/vault-clone/secrets/OPENROUTER_API_KEY").read().strip()
OUT = "/tmp/intern"
import os; os.makedirs(OUT, exist_ok=True)

def free_scan():
    """Newest zero-cost chat models on the public OpenRouter index."""
    req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                 headers={"User-Agent": "zai-agent-intern"})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.load(r)["data"]
    out = []
    for m in rows:
        p = m.get("pricing", {})
        if p.get("prompt") != "0" or p.get("completion") != "0":
            continue
        modality = (m.get("architecture") or {}).get("modality") or ""
        if "text" not in modality.split("->")[0]:
            continue  # image/video/audio generators are not internship material
        out.append((m.get("created", 0), m["id"], m.get("context_length")))
    out.sort(reverse=True)
    return out

def ask(model, prompt, maxtok=3000):
    """One battery task. Paced + 429-aware: free tiers cap RPM/day, so a
    429 honors Retry-After (or linear backoff) and retries; a run that
    stays throttled returns an honest ERR row, never a fabricated score."""
    body = json.dumps({"model": model,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": maxtok, "temperature": 0}).encode()
    last = ""
    for attempt in range(4):
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
            data=body, headers={"Authorization": "Bearer " + KEY,
                                "Content-Type": "application/json",
                                "User-Agent": "zai-agent-intern"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            ch = d["choices"][0]["message"]
            cost = d.get("usage", {}).get("cost", 0)
            time.sleep(4)  # pacing: ~15 req/min, under the free RPM ceiling
            return (ch.get("content") or ""), (ch.get("reasoning") or ""), cost
        except urllib.error.HTTPError as e:
            last = "ERR:HTTP %s" % e.code
            if e.code != 429:
                return "", last, 0  # 403 etc. is a hard wall, not a wait
            wait = int(e.headers.get("Retry-After") or 0) or 15 * (attempt + 1)
            time.sleep(wait)
        except Exception as e:
            return "", "ERR:%s" % e, 0
    return "", last, 0

TASKS = {
"T1-write": """Write ONE Emacs Lisp defun: (agent-intern--todo-parse LINE) -> cons (STATE . TITLE).
LINE examples: "** TODO fix the parser", "** DONE ship it", "** WAITING review", "plain text", "** TODO".
Rules: if LINE starts with the two-char prefix "** " followed by an ALL-CAPS word ([A-Z]+) and then either end-of-string or a space, return (KEYWORD . rest) where rest is everything after the keyword and one space (empty string if end). Otherwise return (nil . LINE). Include a docstring. Output ONLY one code block.""",

"T2-fix": """This Emacs Lisp function is buggy. It must return the FIRST line of TEXT that starts with the PREFIX, or nil. Fix it. Output ONLY one code block with the corrected function.
(defun agent-intern--first-prefixed (prefix text)
  "Return the first line of TEXT starting with PREFIX, or nil."
  (let ((lines (split-string text "\\n")))
    (catch 'found
      (dolist (line lines)
        (when (string= prefix line)
          (throw 'found line))))))""",

"T3-conventions": """Refactor to our conventions: docstring must be a complete first sentence, use `setq-local` not `setq` for buffer-locals, prefer `seq-filter` over cl-loop. Output ONLY one code block.
(defun agent-intern--collect (buf)
  "collect todo lines"
  (with-current-buffer buf
    (setq my-collected nil)
    (cl-loop for l in (split-string (buffer-string) "\\n")
             when (string-prefix-p "** " l) collect l into out
             finally return out)))""",

"T4-api": """Answer with ONE letter per line, nothing else. (1) Which returns a NEW list? a) mapc b) mapcar. (2) Buffer-local binding that survives with-current-buffer? a) setq b) setq-local c) let. (3) Does `string-prefix-p "a" "ab"` return t? a) yes b) no. (4) `buffer-string` returns? a) whole buffer text b) current line c) region.""",
}

def grade(t, out_txt):
    s = 0; notes = []
    code = out_txt
    m = re.search(r"```(?:elisp|emacs-lisp|el)?\s*\n(.*?)```", out_txt, re.S)
    if m: code = m.group(1)
    if t == "T1-write":
        checks = [("defun", "defun agent-intern--todo-parse" in code),
                  ("docstring", '"' in code and ('"Return' in code or '"If' in code or 'docstring' in code.lower() or '\n  "' in code)),
                  ("prefix ** ", ("**" in code and ("string-prefix-p" in code or "string-match" in code))),
                  ("caps word", re.search(r'[A-Z]+', code) is not None or "upper-case-p" in code),
                  ("cons return", ("cons" in code) or re.search(r'\(\s*kw', code) or "(nil" in code)]
        s = sum(1 for _, ok in checks if ok); notes = ["%s=%s" % (n, ok) for n, ok in checks]
    elif t == "T2-fix":
        checks = [("not string= whole line", "(string= prefix line)" not in code),
                  ("prefix-p used", "string-prefix-p" in code),
                  ("dolist/catch kept", "dolist" in code),
                  ("docstring kept", '"Return the first line' in code)]
        s = sum(1 for _, ok in checks if ok); notes = ["%s=%s" % (n, ok) for n, ok in checks]
    elif t == "T3-conventions":
        checks = [("docstring complete sentence", re.search(r'"[A-Z][^"]*\."', code) is not None),
                  ("setq-local", "setq-local" in code),
                  ("no cl-loop", "cl-loop" not in code),
                  ("seq-filter", "seq-filter" in code)]
        s = sum(1 for _, ok in checks if ok); notes = ["%s=%s" % (n, ok) for n, ok in checks]
    elif t == "T4-api":
        letters = re.findall(r'[abcd]', out_txt.lower())
        want = list("bbaa")  # 1:mapcar=b 2:setq-local=b 3:yes=a 4:whole=a
        s = sum(1 for g, w in zip(letters, want) if g == w)
        notes = ["answers=%s" % "".join(letters[:4])]
    return s, notes

MODELS = ["inclusionai/ling-3.1-flash", "inclusionai/ling-3.0-flash"]
argv = sys.argv[1:]
if argv == ["--free-scan"]:
    for created, mid, ctx in free_scan():
        when = time.strftime("%Y-%m-%d", time.gmtime(created)) if created else "?"
        print("%s | ctx=%s | added=%s" % (mid, ctx, when))
    sys.exit(0)
if argv:
    MODELS = argv
scorecards = {}
for model in MODELS:
    sc = {}
    for t, prompt in TASKS.items():
        content, reasoning, cost = ask(model, prompt)
        score, notes = grade(t, content if content.strip() else reasoning)
        sc[t] = (score, notes, cost, (content or reasoning)[:400])
        print("%s | %s | %d | %s" % (model.split("/")[1], t, score, ",".join(notes)))
    scorecards[model] = sc
    print()

json.dump(scorecards, open(OUT + "/scorecards.json", "w"), indent=1)
print("saved", OUT + "/scorecards.json")
