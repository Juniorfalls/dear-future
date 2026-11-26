#!/usr/bin/env python3
"""edge-tts voiceover from math_engine/assets/episode.json + word timings."""
import asyncio, json, subprocess, sys
from pathlib import Path
import edge_tts

OUT = Path("math_engine/assets")
VOICE = "en-US-GuyNeural"
RATE = "+15%"

async def main():
    ep = json.loads((OUT / "episode.json").read_text())
    text = ep.get("speech") or ep["narration"]
    OUT.mkdir(parents=True, exist_ok=True)
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    words, mp3 = [], OUT / "vo.mp3"
    with open(mp3, "wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append({"word": chunk["text"], "start": round(s, 3),
                              "end": round(s + chunk["duration"] / 1e7, 3)})
    (OUT / "vo_words.json").write_text(json.dumps(words, indent=1))
    (OUT / "script.txt").write_text(text + "\n")
    print("words", len(words), "end", words[-1]["end"])

asyncio.run(main())
