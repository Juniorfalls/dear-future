#!/usr/bin/env python3
"""Beat 1 voice + trigger times for the kinetic data visualizer."""
import asyncio, json, os, re, subprocess
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"
VOICE = "en-US-GuyNeural"
RATE = "+8%"
SCRIPT = ("Here is one hundred dollars. It drops by fifty percent. That leaves fifty. "
          "Then it gains fifty percent of fifty, adding twenty five. You land at seventy five. "
          "Most people expect one hundred again. But percentages don't work that way. "
          "The dashed line marks the missing twenty five. "
          "That is why a fifty percent gain cannot undo a fifty percent loss.")

def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower())

async def main():
    com = edge_tts.Communicate(SCRIPT, VOICE, rate=RATE, boundary="WordBoundary")
    words, audio = [], bytearray()
    async for ch in com.stream():
        if ch["type"] == "audio": audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"word": ch["text"], "start": ch["offset"]/1e7,
                          "end": (ch["offset"]+ch["duration"])/1e7})
    (PUB / "vo_beat.mp3").write_bytes(audio)
    (PUB / "vo_words.json").write_text(json.dumps(words, indent=1) + "\n")
    toks = [norm(w["word"]) for w in words]
    def find(seq, after=0.0):
        for i in range(len(toks)):
            if words[i]["start"] < after: continue
            if all(i+k < len(toks) and toks[i+k] == s for k, s in enumerate(seq)):
                return round(words[i]["start"], 3)
        return None
    t_bar = find(["one", "hundred", "dollars"])
    t_drop = find(["drops", "by", "fifty"])
    t_50 = find(["leaves", "fifty"])
    t_gain = find(["gains", "fifty"])
    t_land = find(["land", "at", "seventy"])
    t_dash = find(["dashed", "line"])
    t_gap = find(["missing", "twenty"])
    t_rule = find(["percentages", "dont", "work"])
    beat = {
        "title": "The 50% Trap", "subtitle": "Why +50% does not undo -50%",
        "duration": 25, "script": SCRIPT,
        "triggers": {"bar": t_bar, "drop": t_drop, "fifty": t_50, "gain": t_gain,
                     "land": t_land, "dashed": t_dash, "gap": t_gap, "rule": t_rule},
        "words": words,
    }
    (PUB / "beat.json").write_text(json.dumps(beat, indent=2) + "\n")
    ff = os.environ.get("FFMPEG", "ffmpeg")
    subprocess.run([ff, "-y", "-v", "error", "-i", str(PUB/"vo_beat.mp3"), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", str(PUB/"vo_beat_norm.mp3")], check=True)
    (PUB/"vo_beat_norm.mp3").replace(PUB/"vo_beat.mp3")
    print(json.dumps(beat["triggers"], indent=1))
    print("end", words[-1]["end"], "words", len(words))

asyncio.run(main())
