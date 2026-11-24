# Archived AnimateDiff pipeline

These files powered the retired GPU/AnimateDiff render path. They are kept for
reference only and are no longer part of the active pipeline.

The active, CPU-only engine is `make_horror_stickman.py`, which drives the
[stickman skill](https://github.com/krishnagoswami52/stickman-skill)
(Playwright + Canvas) and Kokoro-82M for voiceover.

| File | Was used for |
| --- | --- |
| `generate_video_free.py` | local AnimateDiff / SD1.5 clip renderer |
| `requirements-video.txt` | CUDA-torch dependency set for the renderer |
| `make_grid.py` | 3x3 Pollinations storyboard panels for AnimateDiff image-to-video conditioning |
| `make_horror_prompts.py` | per-clip AnimateDiff / Colab prompt pack |
| `sound_design.sh` | grade + mix the nine AnimateDiff clips into the teaser |
| `sound_design_mix.sh` | alternative delivery mix for an already-graded AnimateDiff picture |

The episode scripts (`episodes/*.json`) and cast references are still valid
source material and are read by the new wrapper.
