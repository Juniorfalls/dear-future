#!/usr/bin/env python3
"""Turn a topic into the narration script the film is built from.

One entry per scene, in shooting order, with the framing and grade the episode
should use. The text is what Kokoro speaks ("generate_voice.py") and what the
subtitles are chunked from; `duration_hint` is only a planning estimate, since
the real shot length comes from the generated audio.

    python3 generate_script.py "The Fall of Rome"
    python3 generate_script.py --list

Writes remotion/data/script.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "remotion" / "data" / "script.json"

# The voice used unless --voice overrides it. am_michael is the calmer of the
# two deep American male voices; am_adam reads more clipped.
DEFAULT_VOICE = "am_michael"

# One hardcoded episode for now. Scenes alternate the hybrid framing: the host
# opens and closes, the body is b-roll, and the grade carries the place — cold
# for night interiors, warm for daylight.
SCRIPTS: dict[str, dict] = {
    "The Fall of Rome": {
        "scenes": [
            {
                "scene_id": 1,
                "layout": "host_full",
                "grade": "warm",
                "text": "Rome did not fall in a day. It took centuries.",
                "kicker": "The Fall of Rome",
                "duration_hint": 3.5,
            },
            {
                "scene_id": 2,
                "layout": "broll_only",
                "grade": "cold",
                "text": "By the fourth century, the empire was split in two.",
                "duration_hint": 4.0,
            },
            {
                "scene_id": 3,
                "layout": "host_pip",
                "grade": "warm",
                "text": "In the west, the legions were recalled, and the frontier was left open.",
                "duration_hint": 5.0,
            },
            {
                "scene_id": 4,
                "layout": "broll_only",
                "grade": "cold",
                "text": "In four seventy-six, a boy emperor was deposed. No one called it an ending.",
                "duration_hint": 5.5,
            },
            {
                "scene_id": 5,
                "layout": "host_full",
                "grade": "neutral",
                "text": "The empire fell. But the idea of Rome never did.",
                "kicker": "The Fall of Rome",
                "duration_hint": 4.0,
            },
        ]
    }
}


def build(topic: str, voice: str = DEFAULT_VOICE) -> dict:
    if topic not in SCRIPTS:
        sys.exit(
            f'generate_script: no script for "{topic}". Known topics: '
            + ", ".join(sorted(SCRIPTS))
            + ". Add one to SCRIPTS."
        )
    scenes = SCRIPTS[topic]["scenes"]
    return {
        "_notes": (
            "Narration source. generate_voice.py speaks each scene and writes "
            "the wavs plus the real durations back into scenes.json."
        ),
        "topic": topic,
        "voice": voice,
        "scenes": scenes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic", nargs="?", default="The Fall of Rome")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="Kokoro voice id (default: am_michael)")
    ap.add_argument("--out", default=str(OUT), help="output path (default: remotion/data/script.json)")
    ap.add_argument("--list", action="store_true", help="list the topics that have a script")
    ap.add_argument("--print", dest="print_only", action="store_true", help="print, do not write")
    args = ap.parse_args()

    if args.list:
        for name, script in SCRIPTS.items():
            print(f"{name} ({len(script['scenes'])} scenes)")
        return

    doc = build(args.topic, args.voice)
    text = json.dumps(doc, indent=2) + "\n"
    if args.print_only:
        print(text, end="")
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    total = sum(s["duration_hint"] for s in doc["scenes"])
    print(f"wrote {out} — {len(doc['scenes'])} scenes, ~{total:.1f}s of narration planned")
    for s in doc["scenes"]:
        print(f"  {s['scene_id']}. [{s['layout']}/{s['grade']}] {s['text']}")


if __name__ == "__main__":
    main()
