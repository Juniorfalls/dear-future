#!/usr/bin/env python3
"""series.json + episode.json -> horror prompt pack.

Adapted from 10291124jcjc-dotcom/ai-anime-series, where each episode is built
from a character sheet, one grid storyboard and one timed video prompt. Here the
same three prompts are written for an original 2D horror short:

  prompts/character_<id>.txt     one sheet per cast member
  prompts/setting_<id>.txt       the creepy location, no characters
  prompts/01_storyboard_grid.txt the 3x3 pencil board
  prompts/02_video.txt           one 30s video prompt (timed shots + sound)
  prompts/shots/shot-01.txt ...  the same shots as per-clip prompts for Colab
  prompts/overlay_plan.txt       subtitle text and timing for Remotion

Usage
-----
    python make_horror_prompts.py
    python make_horror_prompts.py --series series.json --episode episode.json
    python make_horror_prompts.py --check
    python make_horror_prompts.py --panel 4
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
COPY_MARKER = "------------------------ copy everything below ------------------------"
GRIDS = {6: (2, 3), 9: (3, 3), 12: (3, 4)}
MIN_SHOT_SECONDS = 2.0
MAX_SHOT_SECONDS = 5.0
MAX_CAPTION_CHARS = 46


class PromptError(Exception):
    """An authoring problem in series.json or episode.json."""


def load(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"file not found: {path}")
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}")
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def fmt(value: float) -> str:
    return ("%.1f" % value).rstrip("0").rstrip(".")


def grid_of(count: int) -> tuple[int, int]:
    if count in GRIDS:
        return GRIDS[count]
    cols = max(1, math.ceil(math.sqrt(count)))
    return math.ceil(count / cols), cols


def pick(items: list[dict[str, Any]], ids: list[str], what: str) -> list[dict[str, Any]]:
    by_id = {item.get("id"): item for item in items}
    missing = [item_id for item_id in ids if item_id not in by_id]
    if missing:
        raise PromptError(f"episode.json names {what} not in series.json: {missing}")
    return [by_id[item_id] for item_id in ids]


def shot_list(episode: dict[str, Any]) -> list[dict[str, Any]]:
    parts = episode.get("parts")
    if not isinstance(parts, list) or not parts:
        raise PromptError("episode.json has no parts[].shots")
    if len(parts) > 1:
        raise PromptError(
            "this 30-second pipeline expects one parts[] entry; split longer "
            "episodes into separate episode files"
        )
    shots = parts[0].get("shots")
    if not isinstance(shots, list) or not shots:
        raise PromptError("episode.parts[0].shots is empty")
    return shots


def validate(series: dict[str, Any], episode: dict[str, Any]) -> dict[str, Any]:
    if not text(series.get("style")):
        raise PromptError("series.style is required: the look every panel shares")
    if not text(series.get("title")):
        raise PromptError("series.title is required")
    duration = episode.get("duration")
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise PromptError("episode.duration must be a positive number of seconds")

    shots = shot_list(episode)
    total = 0.0
    seen_panels: set[int] = set()
    for index, shot in enumerate(shots, 1):
        label = f"shot {index}"
        seconds = shot.get("dur")
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            raise PromptError(f"{label}: dur must be a positive number")
        if seconds < MIN_SHOT_SECONDS:
            raise PromptError(f"{label}: {fmt(seconds)}s is too short; {MIN_SHOT_SECONDS}s minimum")
        if seconds > MAX_SHOT_SECONDS:
            print(
                f"warning: {label} holds {fmt(seconds)}s; over {MAX_SHOT_SECONDS}s "
                "the scare loses tension",
                file=sys.stderr,
            )
        if not text(shot.get("desc")):
            raise PromptError(f"{label}: desc is required (what the camera sees)")
        panel = shot.get("panel", index)
        if not isinstance(panel, int) or isinstance(panel, bool):
            raise PromptError(f"{label}: panel must be an integer")
        if panel < 1 or panel > len(shots):
            raise PromptError(f"{label}: panel {panel} is outside 1..{len(shots)}")
        if panel in seen_panels:
            raise PromptError(f"{label}: panel {panel} is used twice")
        seen_panels.add(panel)
        caption = text(shot.get("caption"))
        if not caption:
            print(f"warning: {label} has no caption; Remotion will render it silent", file=sys.stderr)
        elif len(caption) > MAX_CAPTION_CHARS:
            print(
                f"warning: {label} caption is {len(caption)} characters; over "
                f"{MAX_CAPTION_CHARS} will wrap",
                file=sys.stderr,
            )
        total += float(seconds)

    if abs(total - float(duration)) > 0.05:
        raise PromptError(
            f"shots add up to {fmt(total)}s, but episode.duration is "
            f"{fmt(float(duration))}s; make them match"
        )
    rows, cols = grid_of(len(shots))
    if len(shots) != rows * cols:
        raise PromptError(f"a {rows}x{cols} grid needs {rows * cols} shots, found {len(shots)}")

    cast = pick(series.get("characters", []), episode.get("cast", []), "characters")
    groups = pick(series.get("groups", []), episode.get("groups", []), "groups")
    scenes = pick(
        series.get("scenes", []), [episode["scene"]] if episode.get("scene") else [], "scene"
    )
    return {
        "shots": shots,
        "cast": cast,
        "groups": groups,
        "scenes": scenes,
        "rows": rows,
        "cols": cols,
        "total": total,
    }


def ref_rows(series: dict[str, Any], model: dict[str, Any], board_name: str) -> list[dict[str, Any]]:
    """Reference order: cast, groups, setting, storyboard last (as in the repo)."""
    refs: list[dict[str, Any]] = []
    for character in model["cast"]:
        refs.append({"kind": "char", "name": character["name"], "file": text(character.get("ref")),
                     "item": character})
    for group in model["groups"]:
        if text(group.get("ref")):
            refs.append({"kind": "group", "name": group["name"], "file": text(group["ref"]),
                         "item": group})
    for scene in model["scenes"]:
        if text(scene.get("ref")):
            refs.append({"kind": "scene", "name": scene["name"], "file": text(scene["ref"]),
                         "item": scene})
    refs.append({"kind": "board", "name": "storyboard", "file": board_name, "item": None})
    for number, ref in enumerate(refs, 1):
        ref["n"] = number
    return refs


def character_prompt(series: dict[str, Any], character: dict[str, Any]) -> str:
    expressions = ", ".join(character.get("expressions") or [])
    poses = ", ".join(character.get("poses") or [])
    if not expressions:
        expressions = "neutral, startled, terrified, relieved, frozen"
    if not poses:
        poses = "standing, turning, crouching, backing away"
    expr_count = len(character.get("expressions") or [1] * 5)
    pose_count = len(character.get("poses") or [1] * 4)
    header = (
        f"[character sheet | {series.get('ratio', '16:9')} | 1:1 also fine | "
        f"save as {text(character.get('ref')) or 'refs/' + character['id'] + '.jpg'}]"
    )
    body = (
        f"Character sheet for an original 2D horror animation: {character['name']} "
        f"({text(character.get('role')) or 'character'}). "
        f"Full-body three-view (front, side, back), {expr_count} expressions "
        f"({expressions}), {pose_count} poses ({poses}) and a clean silhouette. "
        "Consistent proportions in every view, clean layout, name in the top-left.\n\n"
        f"Character: {character['look']}.\n"
        f"Horror detail: {text(character.get('ability'))}.\n"
        f"Personality: {text(character.get('personality'))}.\n"
        f"{series.get('sheet_style', '')}\n\n"
        "No other characters, no gore, no text beyond the name."
    )
    return f"{header}\n{COPY_MARKER}\n\n{body}\n"


def setting_prompt(series: dict[str, Any], scene: dict[str, Any], time_of_day: str) -> str:
    header = (
        f"[setting sheet | {series.get('ratio', '16:9')} | "
        f"save as {text(scene.get('ref')) or 'refs/' + scene['id'] + '.jpg'}]"
    )
    body = (
        f"Environment reference sheet with no characters: {scene['name']}, "
        f"{time_of_day}. {scene['look']}.\n"
        "Wide establishing composition, one light source doing most of the work, "
        "deep shadows, room for a figure at the edge of the frame. "
        f"{series.get('style', '')}\n"
        "No people, no text, no logo, no watermark."
    )
    return f"{header}\n{COPY_MARKER}\n\n{body}\n"


def character_ref_lines(refs: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for ref in refs:
        if ref["kind"] == "char":
            character = ref["item"]
            lines.append(
                f"Image {ref['n']} is {character['name']}. The character must match "
                f"this sheet exactly: {character['look']}. "
                f"Signature behaviour: {text(character.get('ability'))}."
            )
        elif ref["kind"] == "group":
            lines.append(f"Image {ref['n']} is {ref['name']}: {ref['item']['look']}.")
    return lines


def storyboard_prompt(series: dict[str, Any], episode: dict[str, Any], model: dict[str, Any],
                      refs: list[dict[str, Any]], board_out: str) -> str:
    shots = model["shots"]
    rows, cols = model["rows"], model["cols"]
    who = ", ".join(
        f"Image {ref['n']} is {ref['name']}" for ref in refs if ref["kind"] in ("char", "group")
    )
    scene = model["scenes"][0] if model["scenes"] else None
    selected = ", ".join(ref["name"] + " sheet" for ref in refs if ref["kind"] != "board")
    header = (
        f"[storyboard grid | image generation | attach: {selected} | "
        f"{series.get('ratio', '16:9')} | save as {board_out}]"
    )
    lines = [
        f"Generate one {series.get('ratio', '16:9')} storyboard grid with {rows} rows "
        f"and {cols} columns ({len(shots)} panels) for a {fmt(model['total'])}-second "
        "2D horror animation.",
        "Style: black-and-white pencil sketch, clean confident line work, white paper, "
        "no shading clutter, no extra objects, no lettering or captions inside the "
        f"panels. Number each panel 1 to {len(shots)} in its top-left corner.",
        "Composition: keep the negative space frightening. Put the threat at the edge "
        "of the frame or behind glass, never dead centre, except in the final scare.",
    ]
    if who:
        lines.append(f"Character reference: {who}.")
    if scene:
        lines.append(
            f"All {len(shots)} panels take place in the same {scene['name']} at the "
            f"same {episode.get('time', 'time')}: {scene['look']}."
        )
    lines.append("")
    for index, shot in enumerate(shots, 1):
        panel = shot.get("panel", index)
        description = text(shot.get("sketch")) or text(shot["desc"])
        lines.append(f"Panel {panel}: {description}.")
    lines += [
        "",
        "The camera language is slow push-ins, held wide shots and hard cuts; no "
        "whip pans, no comic angles. Do not draw any text.",
    ]
    return f"{header}\n{COPY_MARKER}\n\n" + "\n".join(lines) + "\n"


def video_prompt(series: dict[str, Any], episode: dict[str, Any], model: dict[str, Any],
                 refs: list[dict[str, Any]], board_name: str) -> str:
    board = next(ref for ref in refs if ref["kind"] == "board")
    scene = model["scenes"][0] if model["scenes"] else None
    lines = [
        f"Animate the storyboard Image {board['n']} as one {fmt(model['total'])}-second "
        "2D horror short. Use it only for shot design, staging, timing and camera; "
        "do not paste or morph the storyboard image itself.",
        "",
    ]
    lines += character_ref_lines(refs)
    if scene:
        lines.append(f"Setting: {scene['name']} at {episode.get('time', 'night')}: {scene['look']}.")
    lines += ["", f"Look: {series.get('style', '')}"]
    if not series.get("dialogue"):
        lines.append("No dialogue. Sound and silence carry the scene.")
    if episode.get("continuity"):
        lines.append("")
        lines.append(
            "Continuity: " + " ".join(
                f"- {item}" for item in episode["continuity"] if text(item)
            )
        )
    lines += ["", "Shots:"]
    cursor = 0.0
    for index, shot in enumerate(model["shots"], 1):
        end = cursor + float(shot["dur"])
        lines.append(
            f"Shot {shot.get('panel', index)} | {fmt(cursor)}-{fmt(end)}s: {shot['desc']}"
        )
        if text(shot.get("sfx")):
            lines.append(f"Sound: {shot['sfx']}")
        if text(shot.get("caption")):
            lines.append(f"Subtitle to add later in Remotion (do not bake into the frame): {shot['caption']}")
        lines.append("")
        cursor = end
    lines += [
        "Hard cuts only. Keep the product of each shot stable: the same character "
        "silhouette, the same coat, the same station. No text, captions, subtitles, "
        "logos or watermarks anywhere in the frame. No stock footage, no photoreal "
        "actors, no gore, no jump-scare montage.",
    ]
    selected = ", ".join(
        f"Image {ref['n']} {ref['name']}" for ref in refs
    )
    header = (
        f"[video generation | {series.get('ratio', '16:9')} | {fmt(model['total'])}s | "
        f"references: {selected} | first pass low resolution, then upscale]"
    )
    return f"{header}\n{COPY_MARKER}\n\n" + "\n".join(lines) + "\n"


def shot_prompt(series: dict[str, Any], episode: dict[str, Any], model: dict[str, Any],
                shot: dict[str, Any]) -> str:
    scene = model["scenes"][0] if model["scenes"] else None
    parts = [
        f"{series.get('style', '')}",
        f"Setting: {scene['look']}." if scene else "",
        f"Action: {shot['desc']}",
        "One continuous shot, hard cut at the end.",
        "No text, captions, subtitles, logos or watermark. No photoreal actors, no gore.",
    ]
    return " ".join(part.strip() for part in parts if part.strip()) + "\n"


def overlay_plan(episode: dict[str, Any], model: dict[str, Any]) -> str:
    lines = [f"{episode.get('title', 'Untitled')} - subtitle plan", ""]
    cursor = 0.0
    for index, shot in enumerate(model["shots"], 1):
        end = cursor + float(shot["dur"])
        caption = text(shot.get("caption"))
        lines.append(
            f"{fmt(cursor):>4}s - {fmt(end):>4}s  [{shot.get('panel', index)}]  "
            f"{caption or '(silent)'}"
        )
        cursor = end
    return "\n".join(lines).rstrip() + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--series", default=str(ROOT / "series.json"))
    parser.add_argument("--episode", default=str(ROOT / "episode.json"))
    parser.add_argument("--out", default=str(ROOT / "prompts"))
    parser.add_argument("--check", action="store_true", help="validate without writing")
    parser.add_argument("--panel", type=int, help="write only one storyboard panel prompt")
    args = parser.parse_args(argv)

    series_path = Path(args.series).resolve()
    episode_path = Path(args.episode).resolve()
    series = load(series_path)
    episode = load(episode_path)
    try:
        model = validate(series, episode)
    except PromptError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    slug = str(episode.get("slug") or episode.get("title") or "episode").lower()
    slug = "".join(character if character.isalnum() else "-" for character in slug).strip("-")
    out_dir = Path(args.out).resolve()
    board_name = f"storyboards/{slug}/storyboard_grid.png"
    refs = ref_rows(series, model, board_name)

    if args.check:
        print(
            f"OK: {len(model['shots'])} panels, {fmt(model['total'])}s, "
            f"{model['rows']}x{model['cols']}, {len(refs)} references"
        )
        return 0

    if args.panel:
        if args.panel < 1 or args.panel > len(model["shots"]):
            raise SystemExit(f"--panel must be 1..{len(model['shots'])}")
        shot = model["shots"][args.panel - 1]
        body = (
            f"Generate one panel of a black-and-white pencil horror storyboard, "
            f"same aspect as one cell of a {model['rows']}x{model['cols']} grid. "
            f"Clean line work, no text except the number {args.panel} in the top-left.\n\n"
            f"Panel {args.panel}: {text(shot.get('sketch')) or text(shot['desc'])}."
        )
        write(out_dir / "storyboard_panels" / f"panel-{args.panel:02d}.txt",
              f"[single storyboard panel | {series.get('ratio', '16:9')}]\n"
              f"{COPY_MARKER}\n\n{body}\n")
        return 0

    for character in model["cast"]:
        write(out_dir / f"character_{character['id']}.txt",
              character_prompt(series, character))
    for scene in model["scenes"]:
        write(out_dir / f"setting_{scene['id']}.txt",
              setting_prompt(series, scene, episode.get("time", "night")))

    write(out_dir / "01_storyboard_grid.txt",
          storyboard_prompt(series, episode, model, refs, board_name))
    write(out_dir / "02_video.txt",
          video_prompt(series, episode, model, refs, board_name))
    write(out_dir / "overlay_plan.txt", overlay_plan(episode, model))
    for index, shot in enumerate(model["shots"], 1):
        write(out_dir / "shots" / f"shot-{index:02d}.txt",
              shot_prompt(series, episode, model, shot))

    print()
    print(
        f"OK: {len(model['shots'])} panels, {fmt(model['total'])}s, "
        f"{model['rows']}x{model['cols']}, {len(refs)} references"
    )
    print(f"Missed reference files? Put them at: "
          + ", ".join(ref['file'] for ref in refs if ref['kind'] != 'board'))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
