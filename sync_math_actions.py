#!/usr/bin/env python3
"""Re-time a/b/c pointing to the words in vo_words.json."""
import json
from pathlib import Path

ASSETS = Path("math_engine/assets")
ep = json.loads((ASSETS / "episode.json").read_text())
words = json.loads((ASSETS / "vo_words.json").read_text())
low = [w["word"].lower().strip(".,!?") for w in words]

def after(needle, start=0):
    for i in range(start, len(words)):
        if low[i] == needle:
            return i
    return None

letters = [i for i, w in enumerate(low) if w == "letter"]
idx_a = after("a", letters[0]) if letters else None
idx_b = after("b", letters[1]) if len(letters) > 1 else None
idx_c = after("c", idx_b or 0) if idx_b is not None else None
times = {}
for name, idx in (("a", idx_a), ("b", idx_b), ("c", idx_c)):
    if idx is not None:
        times[name] = max(2.0, words[idx]["start"] - .25)
print("targets", times)

acts = [a for a in ep["actions"] if not (a.get("action") == "pointAt" and a.get("target") in {"a", "b", "c"})]
for name in ("a", "b", "c"):
    if name in times:
        acts.append({"at": round(times[name], 2), "action": "pointAt", "target": name})
acts.append({"at": round(min(ep.get("duration", 30) - 2.2, max(times.values(), default=24) + 3), 2),
             "action": "turnToCamera"})
ep["actions"] = sorted(acts, key=lambda a: a["at"])
(ASSETS / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
out = Path("episodes/math-quadratic.json")
out.write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
print("actions", [(a["action"], a.get("target"), a["at"]) for a in ep["actions"]])
