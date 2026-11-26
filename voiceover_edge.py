#!/usr/bin/env python3
"""edge-tts voiceover with word boundaries (faster, engaging read)."""
import asyncio, json, subprocess, sys
from pathlib import Path
import edge_tts

TEXT = ("To solve for X, we first subtract four from both sides, leaving "
        "two X equals six. Then we divide by two, giving us X equals three.")
VOICE = "en-US-GuyNeural"
RATE = "+15%"
OUT = Path("math_engine/assets")

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    comm = edge_tts.Communicate(TEXT, VOICE, rate=RATE, boundary="WordBoundary")
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
    (OUT / "script.txt").write_text(TEXT + "\n")
    print("words", len(words), "last end", words[-1]["end"])

asyncio.run(main())
