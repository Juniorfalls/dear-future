#!/usr/bin/env python3
"""Generate a structured math-lesson episode with an LLM (with a safe fallback).

usage: generate_math_lesson.py "The Quadratic Formula" --out episodes/math-quadratic.json
The JSON carries narration, KaTeX equations and teacher actions.
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

FALLBACK = {
 "title": "The Quadratic Formula",
 "duration": 30,
 "narration": ("The quadratic formula solves any equation in the form a x squared plus b x "
               "plus c equals zero. Here it is: x equals negative b, plus or minus the square "
               "root of b squared minus four a c, all divided by two a. The letter a is the "
               "coefficient of x squared. The letter b is the coefficient of x. And c is the "
               "constant term. Plug them in, simplify, and you have your solutions."),
 "equations": [
   {"id": "equation_1",
    "latex": r"x = \frac{-b \pm \sqrt{b^{2}-4ac}}{2a}",
    "at": 4.6, "height": 1.95}
 ],
 "actions": [
   {"at": 0.3, "action": "walkTo", "x": 3.3, "z": -2.05},
   {"at": 2.4, "action": "turnToBoard"},
   {"at": 4.0, "action": "writeOnBoard"},
   {"at": 5.5, "action": "pointAt", "target": "equation_1"},
   {"at": 11.5, "action": "turnToCamera"},
   {"at": 18.0, "action": "pointAt", "target": "b"},
   {"at": 20.5, "action": "pointAt", "target": "a"},
   {"at": 23.0, "action": "pointAt", "target": "c"},
   {"at": 26.0, "action": "turnToCamera"},
   {"at": 28.5, "action": "pointAt", "target": "equation_1"}
 ]
}

PROMPT = """You write one short math lesson for a 2.5D classroom video.
Topic: {topic}
Return ONLY JSON with this shape:
{{
 "title": str,
 "duration": 30,
 "narration": "70-85 words, spoken by a warm teacher, no stage directions",
 "equations": [{{"id": "equation_1", "latex": "...", "at": seconds, "height": 1.6-2.1}}],
 "actions": [{{"at": seconds, "action": "walkTo", "x": number, "z": number}},
             {{"at": seconds, "action": "turnToBoard"}},
             {{"at": seconds, "action": "writeOnBoard"}},
             {{"at": seconds, "action": "pointAt", "target": "equation_1"}},
             {{"at": seconds, "action": "turnToCamera"}}]
}}
Use LaTeX KaTeX syntax. Put the main formula in equations. Keep actions between 0 and 29.
"""


def ask(topic: str) -> dict:
    body = json.dumps({"model": "openai", "temperature": .4, "max_tokens": 1200,
                       "messages": [{"role": "user", "content": PROMPT.format(topic=topic)}]}).encode()
    req = urllib.request.Request("https://text.pollinations.ai/openai", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode())
    text = data["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


SPOKEN_FORMULA = ("x equals negative b, plus or minus the square root of b squared "
                  "minus four a c, all divided by two a")


def speech_text(narration: str) -> str:
    """Turn a narrated script containing LaTeX into something a TTS can read."""
    t = narration.replace("²", " squared ").replace("±", " plus or minus ")
    t = re.sub(r"\s*The result is x\s*=.*?(?:\.|$)", f" The result is {SPOKEN_FORMULA}. ", t)
    t = re.sub(r"\\frac\{[^}]*\}\{[^}]*\}", SPOKEN_FORMULA, t)
    t = re.sub(r"\\sqrt\{([^}]*)\}", r"the square root of \1", t)
    t = t.replace("\\pm", " plus or minus ").replace("\\", " ")
    t = re.sub(r"\bax\b", "a x", t)
    t = re.sub(r"\bbx\b", "b x", t)
    t = t.replace(" + ", " plus ").replace(" - ", " minus ").replace(" = ", " equals ")
    t = re.sub(r"\b2a\b", "two a", t)
    t = re.sub(r"=\s*0", "equals zero", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize(d: dict) -> dict:
    assert isinstance(d.get("title"), str) and d["title"]
    assert isinstance(d.get("narration"), str) and len(d["narration"].split()) > 30
    assert d.get("equations") and all("latex" in e and "at" in e for e in d["equations"])
    d.setdefault("duration", 30)
    eq = d["equations"][0]
    if not eq["latex"].lstrip().startswith("x"):
        eq["latex"] = "x = " + eq["latex"]
    eq.setdefault("id", "equation_1"); eq.setdefault("height", 1.85)
    d["speech"] = speech_text(d["narration"])
    # guarantee the teaching beats the video needs, without discarding LLM text
    have = {(a.get("action"), a.get("target")) for a in d.get("actions", [])}
    actions = sorted(d.get("actions", []), key=lambda a: a.get("at", 0))
    actions = [a for a in actions if a.get("action") in {"walkTo", "turnToBoard", "turnToCamera", "writeOnBoard", "pointAt"}]
    if not any(a["action"] == "walkTo" for a in actions):
        actions.insert(0, {"at": .2, "action": "walkTo", "x": 3.3, "z": -2.05})
    for a in actions:
        if a["action"] == "walkTo":
            a["x"] = max(1.8, min(4.2, float(a.get("x", 3.3)))); a["z"] = -2.05
    required = [("turnToBoard", None, 2.4), ("writeOnBoard", None, 4.0),
                ("pointAt", "equation_1", 5.2), ("turnToCamera", None, 12.0),
                ("pointAt", "b", 17.5), ("pointAt", "a", 20.0), ("pointAt", "c", 22.5),
                ("turnToCamera", None, 26.0)]
    for act, tgt, at in required:
        if (act, tgt) in have:
            continue
        a = {"at": at, "action": act}
        if tgt:
            a["target"] = tgt
        actions.append(a)
    d["actions"] = sorted(actions, key=lambda a: a["at"])
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--out", default="episodes/math-lesson.json")
    ap.add_argument("--no-llm", action="store_true")
    o = ap.parse_args()
    data = normalize(dict(FALLBACK))
    if not o.no_llm:
        try:
            data = normalize(ask(o.topic))
            print("generated by LLM")
        except Exception as exc:  # noqa: BLE001
            print("LLM unavailable, using the verified fallback:", exc)
    data = normalize(data)
    out = Path(o.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    asset = Path("math_engine/assets/episode.json")
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("wrote", out, "and", asset, "| equations:", len(data["equations"]))


if __name__ == "__main__":
    main()
