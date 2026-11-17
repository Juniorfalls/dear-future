"""The Magic of Compound Interest — a Manim Community explainer.

Topic id: compound_interest
Style contract: RULE 1 progressive disclosure, RULE 2 colour language,
RULE 3 decoration polish (see prompts/compound_interest_prompt.txt).

$5,000 once, 7% a year, 30 years - all numbers below are consistent:
    5,000 * 1.07**30  = 38,061     (compound)
    5,000 + 350 * 30  = 15,500     (simple interest, +$350 a year)
    1.07**5           -> +2,013 over the first five years
    1.07**25..1.07**30 -> +10,924 over the last five years
    5,000 * 1.07**20  = 19,348     (started ten years late)

Render:  manim -ql scenes/compound_interest.py CompoundInterestScene
"""

from manim import *

# RULE 2 - at most five colours: BLUE (input), GREEN (growth), YELLOW (insight),
# RED (the warning), GREY (structure).
BG = "#1C1C1C"
INK = "#EBEBEB"


class CompoundInterestScene(Scene):
    def construct(self):
        self.camera.background_color = BG  # RULE 2: fixed background

        self.beat_premise()
        self.beat_simple()
        self.beat_compound()
        self.beat_mechanism()
        self.beat_time()

    # ------------------------------------------------------------------ layout
    def build_axes(self):
        """Grey, low-opacity structure only (RULE 2)."""
        axes = Axes(
            x_range=[0, 30, 10],
            y_range=[0, 45, 15],
            x_length=8.0,
            y_length=4.4,
            tips=False,
            axis_config={
                "color": GREY_B,
                "stroke_width": 2,
                "stroke_opacity": 0.55,
                "include_numbers": True,
                "font_size": 18,
            },
            x_axis_config={"numbers_to_include": [0, 10, 20, 30]},
            y_axis_config={"numbers_to_include": [0, 15, 30, 45]},
        ).move_to([-1.4, -0.45, 0])

        for number in axes.x_axis.numbers + axes.y_axis.numbers:
            number.set_color(GREY_B).set_opacity(0.75)

        unit = Text("$k", font_size=20, color=GREY_B)
        unit.move_to(axes.c2p(0, 45)).shift(LEFT * 0.45 + UP * 0.28)
        years = Text("years", font_size=20, color=GREY_B)
        years.next_to(axes.c2p(30, 0), DOWN, buff=0.45).shift(RIGHT * 0.35)
        return axes, VGroup(unit, years)

    def caption(self, text, size=30, color=INK):
        """Lower-third prose. Short sentences only (RULE 1: no clutter)."""
        return Text(text, font_size=size, color=color).to_edge(DOWN, buff=0.35)

    # -------------------------------------------------------------------- beat 1
    def beat_premise(self):
        # ESSENTIAL: just the three givens, nothing else (RULE 1).
        capital = Text("$5,000", font_size=72, color=BLUE).move_to(UP * 0.75)
        rate = Text("at 7% a year", font_size=32, color=INK)
        rate.next_to(capital, DOWN, buff=0.35)

        self.play(Write(capital), run_time=1.2)
        self.wait(1.0)  # short phrase
        self.play(FadeIn(rate, shift=UP * 0.15), run_time=0.8)
        self.wait(1.5)  # full sentence

        years = Text("left alone for 30 years", font_size=32, color=INK)
        years.next_to(rate, DOWN, buff=0.3)
        self.play(FadeIn(years, shift=UP * 0.15), run_time=0.8)
        self.wait(1.5)

        # Clear the frame, then keep only a quiet corner title.
        title = Text("The Magic of Compound Interest", font_size=30, color=INK)
        title.to_corner(UL, buff=0.35)
        self.play(
            FadeOut(VGroup(capital, rate, years)),
            FadeIn(title, shift=DOWN * 0.15),
            run_time=1.0,
        )

        # Structural layer arrives (RULE 2: grey, low opacity) - one element.
        axes, axis_lbl = self.build_axes()
        self.play(Create(axes), FadeIn(axis_lbl), run_time=1.2)
        self.wait(1.0)

        # The starting point: blue = the given input (RULE 2).
        start = Dot(axes.c2p(0, 5), radius=0.07, color=BLUE)
        start_lbl = Text("$5,000", font_size=26, color=BLUE)
        start_lbl.next_to(start, LEFT, buff=0.25)
        self.play(FadeIn(start, scale=1.6), FadeIn(start_lbl), run_time=0.8)
        self.wait(1.0)  # short phrase

        self.title = title
        self.axes = axes
        self.axis_lbl = axis_lbl
        self.start_grp = VGroup(start, start_lbl)

    # -------------------------------------------------------------------- beat 2
    def beat_simple(self):
        cap = self.caption("First, the honest but flat version: simple interest.")
        self.play(FadeIn(cap), run_time=0.8)
        self.wait(1.5)

        # Supporting: one straight line, one label (RULE 1: two elements).
        linear = self.axes.plot(lambda x: 5 + 0.35 * x, x_range=[0, 30], color=BLUE)
        linear.set_stroke(BLUE, width=4)
        simple_lbl = Text("simple interest", font_size=22, color=BLUE)
        simple_lbl.next_to(self.axes.c2p(14, 5 + 0.35 * 14), UP, buff=0.32)

        self.play(Create(linear), run_time=1.6, rate_func=smooth)
        self.play(FadeIn(simple_lbl, shift=UP * 0.1), run_time=0.7)
        self.wait(1.5)

        # Scoreboard row 1 (RULE 3: value sits clear of the curve).
        row_simple = self.score_row(BLUE, "simple", "$15,500")
        row_simple.move_to([4.5, 2.25, 0])
        ended = Dot(self.axes.c2p(30, 15.5), radius=0.07, color=BLUE)
        self.play(FadeIn(row_simple), FadeIn(ended), run_time=0.8)
        self.wait(3.0)  # key comparison

        self.linear = linear
        self.simple_lbl = simple_lbl
        self.row_simple = row_simple
        self.cap = cap

    # -------------------------------------------------------------------- beat 3
    def beat_compound(self):
        # Enriching: the curve bends because interest starts earning interest.
        curve = self.axes.plot(lambda x: 5 * 1.07 ** x, x_range=[0, 30], color=GREEN)
        curve.set_stroke(GREEN, width=5)
        self.play(Create(curve), run_time=2.6, rate_func=linear)

        row_comp = self.score_row(GREEN, "compound", "$38,061")
        row_comp.move_to([4.5, 1.8, 0])
        ended = Dot(self.axes.c2p(30, 38.06), radius=0.07, color=GREEN)
        self.play(FadeIn(row_comp), FadeIn(ended), run_time=0.8)
        self.wait(3.0)  # key insight

        # RULE 3: a brace groups the gap between the two outcomes.
        gap = Line(self.axes.c2p(30, 15.5), self.axes.c2p(30, 38.06))
        brace = Brace(gap, RIGHT, buff=0.1, color=GREY_B)
        gap_lbl = Text("$22,561", font_size=28, color=YELLOW)
        gap_lbl.next_to(brace, RIGHT, buff=0.15)
        sub = Text("earned by growth alone", font_size=20, color=YELLOW)
        sub.next_to(gap_lbl, DOWN, buff=0.12)
        self.play(GrowFromCenter(brace), FadeIn(gap_lbl), run_time=1.0)
        self.play(FadeIn(sub, shift=UP * 0.1), run_time=0.6)
        self.wait(3.0)  # the trap-defining number

        self.curve = curve
        self.row_comp = row_comp
        self.gap_grp = VGroup(brace, gap_lbl, sub)

    # -------------------------------------------------------------------- beat 4
    def score_row(self, color, name, value):
        """Legend row: colour dot, coloured term, neutral number (RULE 2)."""
        row = VGroup(
            Dot(radius=0.06, color=color),
            Text(name, font_size=22, color=color),
            Text(value, font_size=22, color=INK),
        ).arrange(RIGHT, buff=0.18)
        return row

    def beat_mechanism(self):
        # Clear the scoreboard before the next idea (RULE 1: one idea at a time).
        self.play(
            FadeOut(self.row_simple),
            FadeOut(self.row_comp),
            FadeOut(self.gap_grp),
            FadeOut(self.cap),
            run_time=1.0,
        )

        cap = self.caption("The curve is not magic. It is interest on interest.")
        self.play(FadeIn(cap), run_time=0.8)
        self.wait(1.5)

        # Supporting: two five-year slices, same money, very different growth.
        head = Text("growth per 5 years", font_size=22, color=GREY_B)
        first = self.value_row("first 5 years", "+$2,013", GREEN)
        last = self.value_row("last 5 years", "+$10,924", YELLOW)
        block = VGroup(head, first, last).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        block.move_to([4.3, 1.0, 0])

        self.play(FadeIn(head), FadeIn(first), run_time=1.0)
        self.wait(1.5)
        self.play(FadeIn(last, shift=UP * 0.1), run_time=0.8)

        # RULE 3: frame the insight term in yellow.
        box = SurroundingRectangle(last, color=YELLOW, buff=0.15, corner_radius=0.1)
        box.set_stroke(YELLOW, width=3)
        self.play(Create(box), run_time=0.8)
        self.wait(3.0)  # key insight

        self.mech_grp = VGroup(head, first, last, box)
        self.cap2 = cap

    def value_row(self, label, value, color):
        row = VGroup(
            Text(label, font_size=22, color=INK),
            Text(value, font_size=22, color=color),
        ).arrange(RIGHT, buff=0.45)
        return row

    # -------------------------------------------------------------------- beat 5
    def beat_time(self):
        # Solution: time is the ingredient, so show what ten years of waiting costs.
        self.play(FadeOut(self.mech_grp), FadeOut(self.cap2), run_time=0.9)

        cap = self.caption("Time is the ingredient.")
        self.play(FadeIn(cap), run_time=0.8)
        self.wait(1.0)  # short phrase

        # Second half of the sentence, revealed separately (RULE 1: no clutter).
        cap2 = self.caption("Ten years later, the same money ends here.")
        self.play(Transform(cap, cap2), run_time=0.8)
        self.wait(1.5)

        late = self.axes.plot(
            lambda x: 5 * 1.07 ** (x - 10), x_range=[10, 30], color=RED
        )
        late = DashedVMobject(late, num_dashes=48).set_stroke(RED, width=4)
        late_lbl = Text("$19,348", font_size=30, color=RED)
        late_lbl.next_to(self.axes.c2p(30, 5 * 1.07 ** 20), RIGHT, buff=0.25)
        late_tag = Text("10 years late", font_size=20, color=RED)
        late_tag.next_to(late_lbl, DOWN, buff=0.12)

        self.play(Create(late), run_time=2.0, rate_func=smooth)
        self.play(FadeIn(late_lbl, shift=UP * 0.1), run_time=0.7)
        self.play(FadeIn(late_tag), run_time=0.6)
        self.wait(3.0)  # negative outcome, long hold

        # The one line worth remembering (RULE 2: YELLOW = key insight).
        insight = Text("Same money. Same 7%. Half the result.", font_size=34, color=YELLOW)
        insight.move_to([0, -3.35, 0])
        self.play(ReplacementTransform(cap, insight), run_time=1.2)
        self.wait(3.0)

        # Close on the takeaway; nothing new is introduced.
        self.play(
            FadeOut(self.axes),
            FadeOut(self.axis_lbl),
            FadeOut(self.start_grp),
            FadeOut(self.linear),
            FadeOut(self.simple_lbl),
            FadeOut(self.curve),
            FadeOut(late),
            FadeOut(late_lbl),
            FadeOut(late_tag),
            FadeOut(self.title),
            run_time=1.4,
        )
        insight.move_to(UP * 0.15)
        self.play(insight.animate.move_to(ORIGIN), run_time=1.0)
        self.wait(2.5)
