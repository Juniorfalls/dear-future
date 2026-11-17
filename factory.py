"""Automated video factory: turn the topic queue into ready-to-paste LLM prompts.

For every entry in ``topics.json`` this writes ``prompts/<id>_prompt.txt``: the
full Style Contract plus the specific topic, narrative and a concrete task, so the
prompt can be handed straight to a coding agent that writes the Manim scene.

Usage:  python3 factory.py [topics.json] [prompts_dir]
"""

import json
import re
import sys
from pathlib import Path

QUEUE_PATH = Path("topics.json")
PROMPTS_DIR = Path("prompts")


# --------------------------------------------------------------------------- #
# The Style Contract, shared by every generated prompt.
# --------------------------------------------------------------------------- #
STYLE_CONTRACT = """\
## SYSTEM INSTRUCTION: Manim Explainer Video Generator

You are an expert Manim developer and educational motion designer. Your goal is to
write a Python Manim script that produces a beautiful, engaging and highly
educational explainer video. Adhere strictly to this Style Contract in every scene.

### RULE 1: Progressive Disclosure (Pacing & Hierarchy)
Never show everything at once. Build the viewer's understanding layer by layer.
- The 3-Step Reveal: reveal the "Essential" concept first, wait, add "Supporting"
  annotations, wait, then add "Enriching" details.
- Visual limits: never animate more than 3 new visual elements simultaneously.
- Timing: wait 1.0 s after a short phrase, 1.5 s after a full sentence, and 3.0 s
  after a key insight or complex equation before the next major action.

### RULE 2: Color Language (Semantic Meaning)
Colors must encode meaning, not decorate. Classic 3B1B palette, opacity variants for
depth (e.g. BLUE_E for shadows, BLUE_A for highlights).
- Background: #1C1C1C - always set self.camera.background_color = "#1C1C1C".
- BLUE (#58C4DD): income, given inputs, primary neutral objects.
- GREEN (#83C167): savings, outputs, solutions, growth, positive outcomes.
- YELLOW (#FFFF00): the key insight, the "trap", terms currently under discussion.
- RED (#FC6255): errors, leaks, negative outcomes, warnings.
- GREY: structure only - axes, grids, braces, kept at low opacity (~0.15 fill).

### RULE 3: Decoration Polish (Visual Hierarchy)
Use editorial annotations to guide the eye; never paste raw text on the screen.
- Highlights: SurroundingRectangle with buff=0.15 and corner_radius=0.1 around key
  equations or terms, stroked YELLOW.
- Readability: BackgroundRectangle (fill_opacity=0.7, buff=0.2) behind text that sits
  over a graph or moving objects, or set_stroke(BLACK, width=5, background=True).
- Grouping: Brace / BraceLabel to group concepts and add explanatory text.

### NEGATIVE CONSTRAINTS (What to avoid)
- NO stock footage, emojis or clip art.
- NO particle effects, glow, or bouncing/elastic easing - use rate_func=smooth or linear.
- NO cluttered text: long sentences must be split into separate reveals.
- NO more than 4-5 colors in a single scene.
"""

PROMPT_TEMPLATE = """\
{style_contract}
---

## TASK: Generate the Code

Topic: **{title}**
Topic id: `{id}`
Suggested target file: `scenes/{id}.py`

### Narrative brief
{narrative}

### Instructions for the script
1. Import `from manim import *` (Manim Community Edition, v0.19+ API).
2. Create a single Scene class named `{class_name}` in `scenes/{id}.py`.
3. Follow a Problem -> Solution narrative structure matching the brief above.
   Invent concrete numbers, labels and diagrams that make the idea visible; keep
   every number internally consistent.
4. Apply the 3-step Progressive Disclosure, the strict Color Language and the
   Decoration Polish rules to every animation, and add short code comments saying
   which rule is being applied at each step.
5. Keep the total runtime between 45 and 90 seconds. Do not use LaTeX packages
   outside the default texlive set, and do not rely on external assets or fonts.
6. Make sure the script renders with:
   `manim -ql scenes/{id}.py {class_name}`
7. Output ONLY the Python code, then a one-line note on how to render it.
"""


def topic_to_class_name(topic_id):
    """`compound_interest` -> `CompoundInterestScene`."""
    parts = re.split(r"[^0-9a-zA-Z]+", topic_id)
    name = "".join(part.capitalize() for part in parts if part) or "Explainer"
    if name[0].isdigit():
        name = f"Scene{name}"
    return f"{name}Scene"


def load_topics(path):
    """Return the topic queue as a list of dicts."""
    with open(path, "r", encoding="utf-8") as handle:
        topics = json.load(handle)
    if not isinstance(topics, list):
        raise ValueError(f"{path} must contain a JSON array of topic objects")
    return topics


def build_prompt(topic):
    """Render the full prompt text for one topic."""
    title = topic.get("title") or "Untitled topic"
    narrative = topic.get("narrative") or "(no narrative provided)"
    topic_id = (topic.get("id") or "explainer").strip()
    safe_id = re.sub(r"[^0-9a-zA-Z]+", "_", topic_id).strip("_").lower() or "explainer"

    prompt = PROMPT_TEMPLATE.format(
        style_contract=STYLE_CONTRACT,
        title=title,
        id=safe_id,
        narrative=narrative,
        class_name=topic_to_class_name(safe_id),
    )
    return safe_id, prompt


def main(argv=None):
    argv = argv or sys.argv[1:]
    queue_path = Path(argv[0]) if argv else QUEUE_PATH
    out_dir = Path(argv[1]) if len(argv) > 1 else PROMPTS_DIR

    try:
        topics = load_topics(queue_path)
    except FileNotFoundError:
        print(f"error: {queue_path} not found", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: {queue_path} is not a valid topic queue ({exc})", file=sys.stderr)
        return 1

    if not topics:
        print("Topic queue is empty - nothing to generate.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    for index, topic in enumerate(topics, start=1):
        title = topic.get("title") or "<untitled>"
        safe_id, prompt = build_prompt(topic)
        prompt_path = out_dir / f"{safe_id}_prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        print(f"[{index}/{len(topics)}] Generating scene for: {title}")
        print(f"  id: {topic.get('id', '<no id>')}")
        print(f"  narrative: {topic.get('narrative', '')}")
        print(f"  prompt: {prompt_path} ({len(prompt)} chars)")

    print(f"Wrote {len(topics)} prompt(s) to {out_dir}/ from {queue_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
