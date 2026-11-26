#!/usr/bin/env python3
"""Full five-beat voice + global word-synced trigger map."""
import asyncio, json, os, re, subprocess
from pathlib import Path
import edge_tts

PUB = Path(__file__).resolve().parent.parent / "public"
VOICE = "en-US-GuyNeural"; RATE = "+8%"
B1 = ("Here is one hundred dollars. It drops by fifty percent. That leaves fifty. "
      "Then it gains fifty percent of fifty, adding twenty five. You land at seventy five. "
      "Most people expect one hundred again. But percentages don't work that way. "
      "The dashed line marks the missing twenty five. "
      "That is why a fifty percent gain cannot undo a fifty percent loss.")
B2 = ("Now watch the base shrink. Take the same one hundred dollars and split it into ten blocks of ten. "
      "Lose one block, and only ninety remain. To climb back, you need nine dollars. "
      "Nine dollars is ten percent of ninety, but only nine percent of the original hundred. "
      "So the recovery block is already narrower than the block that left. "
      "And every later percentage points at a different total. Ten percent of ninety is nine, but ten percent of one hundred is ten. "
      "The same percentage, a different amount, because the base changed. To recover fifty percent, you must double what is left. "
      "That is why the climb feels harder than the fall. This is the shrinking base.")
B3 = ("Recovery grows faster than the loss. Watch the ladder. "
      "A ten percent drop needs eleven point one percent to recover. "
      "A twenty five percent drop needs thirty three point three. "
      "A fifty percent drop needs one hundred. And an eighty percent drop needs four hundred percent. "
      "The drop is measured from the old base, but the recovery is measured from the new smaller base. "
      "The smaller the base, the larger the climb. "
      "That is why the gold bars stretch wider and wider as the loss deepens. "
      "At ten percent down the gap is small. At eighty percent down, you need five times your money to break even.")
B4 = ("Now two real world traps. First, a price tag. A hundred dollar item is twenty percent off, so you pay eighty. "
      "Then twenty percent tax is added. Tax is charged on eighty, not on the original hundred, so you pay ninety six. "
      "You never get back to one hundred. Second, a rollercoaster. "
      "Two five percent gains compound to one hundred ten point two five. "
      "But one fifty percent gain followed by a fifty percent loss leaves seventy five. "
      "Same two moves, different order, different base. The tax lands after the discount, on a smaller price. "
      "And each rollercoaster percentage is applied to whatever came before.")
B5 = ("So remember the rule. After a loss, the gain is always measured from a smaller base. "
      "A small loss can demand a huge recovery. Ten percent down needs eleven point one up. "
      "Fifty percent down needs one hundred up. Eighty percent down needs four hundred up. "
      "Losses and gains are not symmetric, even when the percentages look equal. "
      "Protect the base, and you protect the compound. That is the fifty percent trap. Keep the base in mind.")
SCRIPT = " ".join([B1, B2, B3, B4, B5])
DURATION = 180

def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower())

async def main():
    com = edge_tts.Communicate(SCRIPT, VOICE, rate=RATE, boundary="WordBoundary")
    words, audio = [], bytearray()
    async for ch in com.stream():
        if ch["type"] == "audio": audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"word": ch["text"], "start": ch["offset"]/1e7,
                          "end": (ch["offset"]+ch["duration"])/1e7})
    (PUB/"vo_beat.mp3").write_bytes(audio)
    (PUB/"vo_words.json").write_text(json.dumps(words, indent=1) + "\n")
    toks = [norm(w["word"]) for w in words]

    def find(seq, after=0.0):
        for i in range(len(toks)):
            if words[i]["start"] < after: continue
            if all(i+k < len(toks) and toks[i+k] == s for k, s in enumerate(seq)):
                return round(words[i]["start"], 3)
        raise SystemExit(f"missing phrase {seq}")

    starts = {
        1: 0.0,
        2: find(["now","watch","the","base"]) - .55,
        3: find(["recovery","grows","faster"]) - .55,
        4: find(["now","two","real"]) - .55,
        5: find(["so","remember","the","rule"]) - .55,
    }
    s = starts
    trg = {
        "b1": {"bar": find(["one","hundred","dollars"]), "drop": find(["drops","by","fifty"]),
               "fifty": find(["leaves","fifty"]), "gain": find(["gains","fifty"]),
               "land": find(["land","at","seventy"]), "rule": find(["percentages","dont","work"]),
               "dashed": find(["dashed","line"]), "gap": find(["missing","twenty"])},
        "b2": {"split": find(["split","it","into"], s[2]), "lose": find(["lose","one","block"], s[2]),
               "nine": find(["need","nine","dollars"], s[2]), "narrow": find(["recovery","block"], s[2]),
               "base": find(["shrinking","base"], s[2])},
        "b3": {"ladder": find(["watch","the","ladder"], s[3]), "ten": find(["ten","percent","drop"], s[3]),
               "t25": find(["twenty","five","percent","drop"], s[3]),
               "fifty": find(["fifty","percent","drop"], s[3]),
               "eighty": find(["eighty","percent","drop"], s[3]),
               "smaller": find(["smaller","the","base"], s[3])},
        "b4": {"price": find(["price","tag"], s[4]), "off": find(["twenty","percent","off"], s[4]),
               "tax": find(["percent","tax"], s[4]), "pay": find(["pay","ninety","six"], s[4]),
               "roller": find(["second","a","rollercoaster"], s[4]),
               "pathA": find(["two","five","percent","gains"], s[4]),
               "pathB": find(["fifty","percent","loss"], s[4]), "order": find(["different","order"], s[4])},
        "b5": {"rule": find(["remember","the","rule"], s[5]), "small": find(["small","loss"], s[5]),
               "t50": find(["fifty","percent","down"], s[5]), "t80": find(["eighty","percent","down"], s[5]),
               "protect": find(["protect","the","base"], s[5]),
               "outro": find(["fifty","percent","trap"], s[5])},
    }
    # beat ends at the next beat start; keep the last one until the composition ends
    beats = []
    for i in range(1, 6):
        beats.append({"id": i, "start": round(s[i], 3),
                      "end": round(s[i+1], 3) if i < 5 else DURATION,
                      "triggers": trg[f"b{i}"]})
    ep = {"title": "The 50% Trap", "duration": DURATION, "script": SCRIPT,
          "voiceEnd": round(words[-1]["end"], 3), "beats": beats, "words": words}
    (PUB/"beat.json").write_text(json.dumps(ep, indent=2) + "\n")
    ff = os.environ.get("FFMPEG", "ffmpeg")
    subprocess.run([ff,"-y","-v","error","-i",str(PUB/"vo_beat.mp3"),"-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11","-ar","48000",str(PUB/"vo_beat_norm.mp3")],check=True)
    (PUB/"vo_beat_norm.mp3").replace(PUB/"vo_beat.mp3")
    print("voice end", words[-1]["end"], "words", len(words))
    for b in beats: print(b["id"], b["start"], b["end"])
    for k,v in trg.items(): print(k, v)

asyncio.run(main())
