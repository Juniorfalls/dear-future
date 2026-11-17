"""Why Losing $10 Hurts More Than Winning $10 — a Manim Community explainer.

Topic id: loss_aversion
Style contract: RULE 1 progressive disclosure, RULE 2 colour language,
RULE 3 decoration polish (see prompts/loss_aversion_prompt.txt).

The one number the scene leans on: loss aversion prices the same 50/50 risk at
roughly 2:1 — a $10 loss feels like a $20 loss, so a $10 win has to look like
$20 before the bet feels fair. Everything below is consistent with that 2:1.

Render:  manim -ql scenes/loss_aversion.py LossAversionScene
"""

import math

import numpy as np
from manim import *

# RULE 2 - five colours only: BLUE (the gain / neutral), RED (the loss),
# YELLOW (the insight), GREEN (the fix), GREY (the structure).
BG = "#1C1C1C"
INK = "#EBEBEB"
PIVOT = np.array([-1.75, -0.15, 0.0])
HALF = 2.15
HANG = 0.95
TILT = 0.17  # radians of imbalance, about 10 degrees


class LossAversionScene(Scene):
    def construct(self):
        self.camera.background_color = BG  # RULE 2: fixed background

        self.beat_premise()
        self.beat_scale()
        self.beat_price()
        self.beat_fix()
        self.beat_insight()

    # ------------------------------------------------------------------ helpers
    def chip(self, head, value, color):
        return VGroup(
            Text(head, font_size=26, color=color),
            Text(value, font_size=58, color=color),
        ).arrange(DOWN, buff=0.15)

    def caption(self, text, size=30, color=INK):
        """Lower-third prose. Short sentences only (RULE 1: no clutter)."""
        return Text(text, font_size=size, color=color).to_edge(DOWN, buff=0.35)

    def pan_centers(self, tilt):
        dx, dy = HALF * math.cos(tilt), HALF * math.sin(tilt)
        return (
            PIVOT + np.array([-dx, dy - HANG, 0]),
            PIVOT + np.array([dx, -dy - HANG, 0]),
        )

    def make_beam(self, tilt):
        """Beam + hanging plates as one path-free group (RULE 2: grey structure)."""
        dx, dy = HALF * math.cos(tilt), HALF * math.sin(tilt)
        left_end = PIVOT + np.array([-dx, dy, 0])
        right_end = PIVOT + np.array([dx, -dy, 0])

        parts = [Line(left_end, right_end, color=GREY_A, stroke_width=6)]
        for end in (left_end, right_end):
            plate_c = end + DOWN * HANG
            parts.append(Line(end, plate_c + LEFT * 0.7 + UP * 0.18,
                              color=GREY_B, stroke_width=2))
            parts.append(Line(end, plate_c + RIGHT * 0.7 + UP * 0.18,
                              color=GREY_B, stroke_width=2))
            parts.append(Line(plate_c + LEFT * 0.8, plate_c + RIGHT * 0.8,
                              color=GREY_A, stroke_width=5))
        return VGroup(*parts)

    def make_stand(self):
        base = PIVOT + DOWN * 2.3
        return VGroup(
            Line(PIVOT, base, color=GREY_B, stroke_width=5),
            Line(base + LEFT * 1.15, base + RIGHT * 1.15,
                 color=GREY_B, stroke_width=5),
            Dot(PIVOT, radius=0.08, color=GREY_A),
        )

    def weight_label(self, text, color, side="left", tilt=0.0):
        """The number sitting on a pan."""
        left_c, right_c = self.pan_centers(tilt)
        center = left_c if side == "left" else right_c
        lbl = Text(text, font_size=34, color=color)
        lbl.move_to(center + UP * 0.42)
        return lbl

    # -------------------------------------------------------------------- beat 1
    def beat_premise(self):
        # ESSENTIAL: the two identical amounts, nothing else (RULE 1).
        win = self.chip("you win", "+$10", BLUE)
        lose = self.chip("you lose", "-$10", RED)
        pair = VGroup(win, lose).arrange(RIGHT, buff=2.3).move_to(UP * 0.55)

        self.play(Write(win), run_time=1.2)
        self.wait(1.0)  # short phrase
        self.play(Write(lose), run_time=1.2)
        self.wait(1.0)

        same = Text("Same amount. Same odds.", font_size=30, color=INK)
        same.next_to(pair, DOWN, buff=1.0)
        self.play(FadeIn(same, shift=UP * 0.15), run_time=0.8)
        self.wait(1.5)  # full sentence

        heavier = Text("But one of them weighs more.", font_size=36, color=YELLOW)
        heavier.next_to(same, DOWN, buff=0.45)
        self.play(FadeIn(heavier, shift=UP * 0.15), run_time=0.8)
        self.wait(3.0)  # key insight

        title = Text("Loss Aversion", font_size=36, color=INK)
        title.to_corner(UL, buff=0.35)
        self.play(
            FadeOut(pair),
            FadeOut(same),
            FadeOut(heavier),
            FadeIn(title, shift=DOWN * 0.15),
            run_time=1.0,
        )

        # Supporting: the metaphor itself, one structural element at a time.
        stand = self.make_stand()
        beam = self.make_beam(0.0)
        self.play(Create(stand), run_time=1.0)
        self.play(Create(beam), run_time=1.2)
        self.wait(1.0)

        self.title = title
        self.stand = stand
        self.beam = beam

    # -------------------------------------------------------------------- beat 2
    def beat_scale(self):
        # Two identical weights: the paper value of the bet (RULE 2: blue / red).
        left_lbl = self.weight_label("$10", BLUE, "left", 0.0)
        right_lbl = self.weight_label("$10", RED, "right", 0.0)
        self.play(FadeIn(left_lbl), FadeIn(right_lbl), run_time=0.9)
        self.wait(1.0)

        cap = self.caption("On paper, both pans hold $10.")
        self.play(FadeIn(cap), run_time=0.8)
        self.wait(1.5)

        # The loss pan sinks: the feeling, drawn (RULE 2: red side drops).
        tilted = self.make_beam(TILT)
        left_c, right_c = self.pan_centers(TILT)
        self.play(
            Transform(self.beam, tilted),
            left_lbl.animate.move_to(left_c + UP * 0.42),
            right_lbl.animate.move_to(right_c + UP * 0.42),
            run_time=1.6,
            rate_func=smooth,  # no bounce / elastic (negative constraint)
        )
        self.wait(3.0)  # key visual insight

        # RULE 3: label the subjective weight beside the sinking pan.
        feel = Text("feels like $20", font_size=26, color=RED)
        feel.next_to(right_c + DOWN * 0.1, DOWN, buff=0.2)
        feel.set_stroke(BLACK, width=5, background=True)  # RULE 3 readability
        self.play(FadeIn(feel, shift=UP * 0.15), run_time=0.8)
        self.wait(1.0)

        self.left_lbl = left_lbl
        self.right_lbl = right_lbl
        self.feel = feel
        self.cap = cap

    # -------------------------------------------------------------------- beat 3
    def beat_price(self):
        # RULE 3: frame the quantitative claim, so it reads as the takeaway.
        stmt = Text("$10 lost stings like $20 won.", font_size=32, color=INK)
        stmt.move_to([0.2, -3.05, 0])
        box = SurroundingRectangle(stmt, color=YELLOW, buff=0.15, corner_radius=0.1)
        box.set_stroke(YELLOW, width=3)

        self.play(FadeOut(self.cap), FadeOut(self.feel), run_time=0.7)
        self.play(Write(stmt), run_time=1.2)
        self.play(Create(box), run_time=0.8)
        self.wait(3.0)  # key insight

        # Enriching: the bet only feels fair when the win is doubled (2:1).
        cap = self.caption("So the win has to look twice as big.")
        self.play(FadeOut(box), FadeOut(stmt), FadeIn(cap), run_time=0.9)
        self.wait(1.5)

        level = self.make_beam(0.0)
        left_c, right_c = self.pan_centers(0.0)
        big_win = self.weight_label("$20", BLUE, "left", 0.0)
        self.play(
            Transform(self.beam, level),
            Transform(self.left_lbl, big_win),
            self.right_lbl.animate.move_to(right_c + UP * 0.42),
            run_time=1.6,
            rate_func=smooth,
        )
        self.wait(1.5)

        claim = Text("Loss aversion prices the same risk at 2:1.", font_size=30, color=INK)
        claim.move_to([0.2, -3.05, 0])
        claim_box = SurroundingRectangle(claim, color=YELLOW, buff=0.15, corner_radius=0.1)
        claim_box.set_stroke(YELLOW, width=3)
        self.play(Transform(cap, claim), run_time=0.9)
        self.play(Create(claim_box), run_time=0.8)
        self.wait(3.0)  # key insight

        self.cap = cap
        self.claim_box = claim_box

    # -------------------------------------------------------------------- beat 4
    def beat_fix(self):
        # Solution layer (RULE 2: green = the fix), one rule per reveal.
        self.play(FadeOut(self.cap), FadeOut(self.claim_box), run_time=0.7)

        head = Text("how to price it back", font_size=22, color=GREY_B)
        rules = VGroup(
            head,
            Text("1  write the loss in dollars", font_size=22, color=GREEN),
            Text("2  size the bet so it cannot sting", font_size=22, color=GREEN),
            Text("3  decide before you feel it", font_size=22, color=GREEN),
        ).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        rules.move_to([4.45, 0.6, 0])

        cap = self.caption("You cannot argue with the feeling.")
        self.play(FadeIn(head), FadeIn(rules[1]), FadeIn(cap), run_time=0.9)
        self.wait(1.5)

        self.play(FadeIn(rules[2], shift=UP * 0.1), run_time=0.7)
        self.wait(1.0)
        self.play(FadeIn(rules[3], shift=UP * 0.1), run_time=0.7)
        self.wait(1.0)

        self.play(
            Transform(cap, self.caption("You can out-plan it.")),
            run_time=0.8,
        )
        self.wait(1.5)

        self.rules = rules
        self.cap = cap

    # -------------------------------------------------------------------- beat 5
    def beat_insight(self):
        # The line worth remembering (RULE 2: YELLOW = key insight).
        insight = Text("The loss is real. The extra weight is not.", font_size=34,
                       color=YELLOW)
        insight.move_to([0.2, -3.05, 0])

        self.play(
            FadeOut(self.rules),
            FadeOut(self.cap),
            FadeOut(self.left_lbl),
            FadeOut(self.right_lbl),
            FadeOut(self.beam),
            FadeOut(self.stand),
            FadeOut(self.title),
            FadeIn(insight),
            run_time=1.4,
        )
        self.wait(3.0)  # key insight

        # Close on the takeaway; nothing new is added.
        insight.move_to([0.2, -3.05, 0])
        self.play(insight.animate.move_to(ORIGIN).scale(1.05), run_time=1.2)
        self.wait(2.5)