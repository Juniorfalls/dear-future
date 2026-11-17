"""Automated video factory: read the topic queue and report what to build.

For now this only walks ``topics.json`` and prints the plan. The LLM scene
generation step plugs in later, right where the ``TODO`` marker is.

Usage:  python3 factory.py [topics.json]
"""

import json
import sys
from pathlib import Path

QUEUE_PATH = Path("topics.json")


def load_topics(path):
    """Return the topic queue as a list of dicts."""
    with open(path, "r", encoding="utf-8") as handle:
        topics = json.load(handle)
    if not isinstance(topics, list):
        raise ValueError(f"{path} must contain a JSON array of topic objects")
    return topics


def main(argv=None):
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else QUEUE_PATH

    try:
        topics = load_topics(path)
    except FileNotFoundError:
        print(f"error: {path} not found", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: {path} is not a valid topic queue ({exc})", file=sys.stderr)
        return 1

    if not topics:
        print("Topic queue is empty - nothing to generate.")
        return 0

    for index, topic in enumerate(topics, start=1):
        title = topic.get("title", "<untitled>")
        narrative = topic.get("narrative", "")
        print(f"[{index}/{len(topics)}] Generating scene for: {title}")
        print(f"  id: {topic.get('id', '<no id>')}")
        print(f"  narrative: {narrative}")
        print(f"  target: scenes/{topic.get('id', 'untitled')}.py")
        # TODO: call the LLM scene generator here and write the scene file.

    print(f"Planned {len(topics)} video(s) from {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
