#!/usr/bin/env python3
"""Generate the 15s 'Solving for X' voice and time the three equation lines."""
import asyncio, json, os, re, subprocess, sys
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"
VOICE = "en-US-GuyNeural"
RATE = "+12%"
SCRIPT = ("Today we solve for x. Start with two x plus three equals eleven. "
          "Subtract three from both sides, and two x equals eight. "
          "Finally, divide by two: x equals four. Now you can solve it too.")


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


async def main():
    com = edge_tts.Communicate(SCRIPT, VOICE, rate=RATE, boundary="WordBoundary")
    words, audio = [], bytearray()
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"word": ch["text"], "start": ch["offset"] / 1e7,
                          "end": (ch["offset"] + ch["duration"]) / 1e7})
    mp3 = PUB / "vo.mp3"
    mp3.write_bytes(audio)
    (PUB / "vo_words.json").write_text(json.dumps(words, indent=1) + "\n")

    def find(seq, after=0.0):
        toks = [norm(w["word"]) for w in words]
        for i in range(len(toks)):
            if words[i]["start"] < after:
                continue
            if all(i + k < len(toks) and toks[i + k] == s for k, s in enumerate(seq)):
                return words[i]["start"]
        return None

    t1 = find(["two", "x", "plus"])
    t2 = find(["two", "x", "equals", "eight"], (t1 or 0) + .1)
    t3 = find(["x", "equals", "four"], (t2 or 0) + .1)
    episode = {
        "title": "Solving for X",
        "script": SCRIPT,
        "duration": 15,
        "lines": [
            {"id": "l1", "latex": "2x + 3 = 11", "plain": "2x+3=11", "at": round(t1 or 2.0, 3)},
            {"id": "l2", "latex": "2x = 8", "plain": "2x=8", "at": round(t2 or 6.0, 3)},
            {"id": "l3", "latex": "x = 4", "plain": "x=4", "at": round(t3 or 10.0, 3)},
        ],
        "actions": [
            {"at": 0.0, "action": "walkTo", "x": -2.55},
            {"at": 1.5, "action": "turnToBoard"},
            {"at": 2.0, "action": "writeOnBoard"},
            {"at": 12.4, "action": "turnToCamera"},
        ],
    }
    (PUB / "episode.json").write_text(json.dumps(episode, indent=2) + "\n")
    subprocess.run([os.environ.get("FFMPEG", "ffmpeg"), "-y", "-v", "error", "-i", str(mp3), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
                    str(PUB / "vo_norm.mp3")], check=True)
    (PUB / "vo_norm.mp3").replace(mp3)
    print("lines", episode["lines"])
    print("words", len(words), "end", words[-1]["end"])

if __name__ == "__main__":
    asyncio.run(main())
