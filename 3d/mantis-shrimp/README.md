# Mantis Shrimp — procedural 3D reconstruction

Built with the [`img2threejs`](https://github.com/img2threejs/img2threejs) skill
(Apache-2.0): "rebuild the object in a reference image as a code-only,
procedural, animation-ready Three.js model". No mesh files, no downloaded art
packs — the creature in `remotion/src/three/MantisShrimp.tsx` is primitives,
pivots and materials, which is why it renders deterministically inside Remotion.

## Install the skill

```bash
npx --yes img2threejs@latest install     # links into hermes/claude/codex/opencode
npx --yes img2threejs@latest doctor
```

This machine has none of those hosts, and the installer exits 2
("no supported agent host detected"), so it was linked manually for the free-pi
agent, exactly as `docs/INSTALL.md` §7 describes:

```bash
mkdir -p ~/.img2threejs && git clone --depth 1 \
  https://github.com/img2threejs/img2threejs.git ~/.img2threejs/skill
ln -sfn ~/.img2threejs/skill .agents/skills/img2threejs
```

`.agents/skills/img2threejs` is gitignored — the checkout is vendored locally,
the skill is not a dependency of this repo.

## What was produced here

| File | Purpose |
|------|---------|
| `assessment.json` | pre-spec assessment + quality contract (`forge/stage2_spec/new_pre_spec_assessment.py`, complexity `complex`, domain `object`) |
| `object-sculpt-spec.json` | the sculpt spec: 9 components, 5 materials, animation anchors, visual evidence |
| `../../remotion/src/three/MantisShrimp.tsx` | the model itself |
| `../../remotion/src/AnimatedAnimalScene.tsx` | environment, camera, lights, text overlay |

Reference image: `remotion/public/animals/mantis-shrimp.jpg`.

## Deliberate simplification

Per the skill's own rule — *state explicitly when output is approximate* — this
is a **stylized, low-poly, plush reconstruction**, not a photogrammetric match:

- one reference view cannot show the hidden sides, so the underside, the exact
  number of swimmerets and the club's internal hinge are invented;
- the colour bands are quantised to five flat materials instead of projected
  texture, because the target look is a soft toy, not chitin;
- eye facets, setae and the tail's fine venation are omitted at this LOD.

Identity-defining features that ARE modelled: segmented banded carapace,
stalked compound eyes, folded raptorial clubs, antennae, eight paddle legs and
the five-blade tail fan.

## Rebuild / re-verify

```bash
cd remotion
npx remotion still AnimalScene out/3d-check.png --frame=90    # blockout + material
npx remotion still AnimalScene out/3d-p255.png  --frame=255   # strike + shockwave
```
