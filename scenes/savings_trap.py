"""The Leaky Bucket Savings Trap — a Manim Community explainer.

Style contract
--------------
RULE 1  Progressive disclosure: Essential -> Supporting -> Enriching, max 3 new
        elements per animation, waits of 1.0 / 1.5 / 3.0 s after phrases,
        sentences and key insights.
RULE 2  Colour language: BLUE = income / given input, GREEN = savings / solution,
        YELLOW = the key insight, RED = leak / loss, GREY = structure only.
RULE 3  Decoration polish: yellow SurroundingRectangle highlights, braces for
        grouping, BackgroundRectangle behind text that sits over the diagram.

Render:  manim -ql scenes/savings_trap.py SavingsTrap
"""

from manim import *

# ----------------------------------------------------------------------------
# RULE 2 — the whole scene uses at most 5 colours: blue, green, yellow, red, grey.
# ----------------------------------------------------------------------------
BG = "#1C1C1C"
INK = "#EBEBEB"


class SavingsTrap(Scene):
    def construct(self):
        self.camera.background_color = BG  # RULE 2: fixed background

        self.beat_title()
        self.beat_leak()
        self.beat_math()
        self.beat_solution()
        self.beat_insight()

    # ------------------------------------------------------------------ helpers
    def caption(self, text, size=30, color=INK):
        """Lower-third subtitle. Short prose only (RULE 1: no clutter), and it sits
        below the diagram so it can never collide with the top-left title."""
        return Text(text, font_size=size, color=color).to_edge(DOWN, buff=0.35)

    def bucket(self, x=-3.1, y_top=0.95, half_top=1.55, half_bot=1.15, h=2.5):
        """Trapezoid bucket, BLUE stroke (primary neutral object)."""
        pts = [
            [-half_top, 0, 0],
            [half_top, 0, 0],
            [half_bot, -h, 0],
            [-half_bot, -h, 0],
        ]
        shape = Polygon(*pts, color=BLUE, stroke_width=5)
        shape.set_fill(BLUE_E, opacity=0.18)  # RULE 2: dark variant for depth
        shape.move_to([x, y_top - h / 2, 0])
        return shape

    def savings_fill(self, bucket, fraction, x=-3.1):
        """Green rectangle = money actually kept. Shrinks when the bucket leaks."""
        bottom = bucket.get_bottom()[1] + 0.06
        height = max(0.12, 2.30 * fraction)
        fill = Rectangle(width=2.35, height=height, color=GREEN, stroke_width=0)
        fill.set_fill(GREEN, opacity=0.55)
        fill.move_to([x, bottom + height / 2, 0])
        return fill

    # -------------------------------------------------------------------- beat 1
    def beat_title(self):
        # ESSENTIAL: the metaphor alone, nothing else on screen (RULE 1).
        title = Text("The Leaky Bucket", font_size=54, color=INK).move_to(UP * 1.2)
        sub = Text("why your savings never grow", font_size=30, color=GREY_B)
        sub.next_to(title, DOWN, buff=0.35)

        self.play(Write(title), run_time=1.2)
        self.wait(1.0)  # short phrase
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.8)
        self.wait(1.5)  # full sentence
        # Settle the title into a quiet corner so the diagram owns the frame.
        self.play(
            FadeOut(sub),
            title.animate.scale(0.55).to_corner(UL, buff=0.35),
            run_time=0.9,
        )

        # ESCALATE: bucket + income arrow — exactly 2 new elements (RULE 1).
        bucket = self.bucket()
        income = Arrow(
            start=[-3.1, 2.05, 0],
            end=[-3.1, 1.15, 0],
            color=BLUE,
            stroke_width=6,
            buff=0.08,
            max_tip_length_to_length_ratio=0.28,
        )
        income_lbl = Text("$100 in", font_size=32, color=BLUE)
        income_lbl.next_to(income, RIGHT, buff=0.35)

        self.play(Create(bucket), run_time=1.2)
        self.play(GrowArrow(income), FadeIn(income_lbl), run_time=1.0)
        self.wait(1.5)

        # Enriching detail: the water level, i.e. the money "safely stored".
        fill = self.savings_fill(bucket, 1.0)
        level_lbl = Text("$100", font_size=34, color=INK)
        level_lbl.move_to([-3.1, 0.42, 0])
        level_lbl.set_stroke(BLACK, width=5, background=True)  # RULE 3 readability

        self.play(FadeIn(fill), run_time=1.0)
        self.play(FadeIn(level_lbl, shift=UP * 0.15), run_time=0.7)
        self.wait(1.5)

        # Store for the next beat (no re-creation, keeps the frame stable).
        self.bucket_mob = bucket
        self.fill_mob = fill
        self.income_grp = VGroup(income, income_lbl)
        self.level_lbl = level_lbl
        self.title = title

    # -------------------------------------------------------------------- beat 2
    def beat_leak(self):
        cap = self.caption("It looks full — until you count what drips out.")
        self.play(FadeIn(cap, shift=DOWN * 0.2), run_time=0.8)
        self.wait(1.5)

        # ESSENTIAL of this beat: one single leak (RULE 1: one element at a time).
        leak = Arrow(
            start=[-2.75, self.bucket_mob.get_bottom()[1] - 0.05, 0],
            end=[-2.75, self.bucket_mob.get_bottom()[1] - 1.15, 0],
            color=RED,
            stroke_width=5,
            buff=0.05,
            max_tip_length_to_length_ratio=0.3,
        )
        leak_lbl = Text("leaks", font_size=28, color=RED)
        leak_lbl.next_to(leak, RIGHT, buff=0.3)
        self.play(GrowArrow(leak), FadeIn(leak_lbl), run_time=1.0)
        self.wait(1.0)

        # Supporting: the three real leaks, revealed one by one on the right.
        rows = VGroup()
        for name, value in [("subscriptions", "22"), ("bank fees", "18"), ("impulse buys", "26")]:
            left = Text(name, font_size=28, color=INK)
            right = Text(f"-${value}", font_size=28, color=RED)
            row = VGroup(left, right).arrange(RIGHT, buff=0.9)
            rows.add(row)
        rows.arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        rows.move_to([2.75, 0.9, 0])

        for row in rows:
            self.play(FadeIn(row, shift=RIGHT * 0.25), run_time=0.7)
            self.wait(1.0)  # short phrase

        # RULE 3: brace groups the leaks into one idea; label stays upright and
        # inside the frame (never rotate it off the right edge).
        brace = Brace(rows, RIGHT, color=GREY_B)
        brace_lbl = Text("leaks", font_size=26, color=YELLOW)
        brace_lbl.next_to(brace, RIGHT, buff=0.2)
        brace_lbl.set_stroke(BLACK, width=4, background=True)
        self.play(GrowFromCenter(brace), FadeIn(brace_lbl), run_time=0.9)
        self.wait(1.5)

        # The level drops: the visual proof the bucket is leaking (RULE 2: green = kept).
        thin_fill = self.savings_fill(self.bucket_mob, 0.34)
        kept = Text("$34 kept", font_size=30, color=YELLOW)
        kept.move_to([-3.1, -0.02, 0])
        kept.set_stroke(BLACK, width=5, background=True)  # RULE 3 readability
        self.play(
            Transform(self.fill_mob, thin_fill),
            Transform(self.level_lbl, kept),
            run_time=1.6,
            rate_func=smooth,  # no bounce / elastic (negative constraint)
        )
        self.wait(3.0)  # key insight

        self.cap1 = cap
        self.leak_grp = VGroup(leak, leak_lbl)
        self.rows = rows
        self.brace_grp = VGroup(brace, brace_lbl)

    # -------------------------------------------------------------------- beat 3
    def beat_math(self):
        # Enriching: the arithmetic that names the trap — one equation, framed.
        eq = MathTex(r"100", r"\;-\;", r"66", r"\;=\;", r"34").scale(0.95)
        eq[0].set_color(BLUE)
        eq[2].set_color(RED)
        eq[4].set_color(YELLOW)
        eq.next_to(self.rows, DOWN, buff=1.2)
        eq.shift(RIGHT * 0.15)

        frame = SurroundingRectangle(eq, color=YELLOW, buff=0.15, corner_radius=0.1)
        frame.set_stroke(YELLOW, width=3, opacity=0.9)

        self.play(Write(eq), run_time=1.2)
        self.wait(1.5)
        # RULE 3: highlight the equation, not the whole screen.
        self.play(Create(frame), run_time=0.9)
        self.wait(3.0)  # complex equation -> long hold

        # RULE 3: brace explains the middle terms without extra prose.
        b = Brace(eq[1:3], DOWN, color=GREY_B)
        b_lbl = b.get_text("everything you never counted", buff=0.18)
        b_lbl.set_color(YELLOW).scale(0.85)
        b_lbl.set_stroke(BLACK, width=4, background=True)
        self.play(GrowFromCenter(b), FadeIn(b_lbl), run_time=1.0)
        self.wait(3.0)

        self.eq_grp = VGroup(eq, frame)
        self.brace2 = VGroup(b, b_lbl)

    # -------------------------------------------------------------------- beat 4
    def beat_solution(self):
        # Clear the scoreboard before the fix (RULE 1: never crowd the frame).
        self.play(
            FadeOut(self.rows),
            FadeOut(self.brace_grp),
            FadeOut(self.brace2),
            FadeOut(self.cap1),
            FadeOut(self.level_lbl),
            FadeOut(self.eq_grp),
            run_time=1.2,
        )
        cap = self.caption("Patch the holes — then the bucket can fill.")
        self.play(FadeIn(cap), run_time=0.8)
        self.wait(1.5)

        # Essential solution object: the leak gets plugged (GREEN = solution).
        plug = Line(
            start=[-2.98, self.leak_grp[0].get_start()[1] - 0.02, 0],
            end=[-2.52, self.leak_grp[0].get_start()[1] - 0.02, 0],
            color=GREEN,
            stroke_width=9,
        )
        cross = Cross(scale_factor=0.25, stroke_width=6).set_color(GREEN)
        cross.move_to(self.leak_grp[0].get_center())
        self.play(FadeOut(self.leak_grp[1]), run_time=0.5)
        self.play(Create(plug), Create(cross), run_time=1.0)
        self.wait(1.0)

        # Supporting: three fixes, one per play call, 3 elements max (RULE 1).
        fixes = VGroup(
            Text("1  pay yourself first", font_size=28, color=GREEN),
            Text("2  cancel unused plans", font_size=28, color=GREEN),
            Text("3  make the goal visible", font_size=28, color=GREEN),
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        fixes.next_to(self.bucket_mob, RIGHT, buff=1.5).shift(UP * 0.9)

        for fix in fixes:
            self.play(FadeIn(fix, shift=RIGHT * 0.25), run_time=0.7)
            self.wait(1.0)

        # Enriching: only $10 still escapes, so the bucket refills (GREEN = growth).
        new_eq = MathTex(r"100", r"\;-\;", r"10", r"\;=\;", r"90").scale(0.85)
        new_eq[0].set_color(BLUE)
        new_eq[2].set_color(RED)
        new_eq[4].set_color(GREEN)
        new_eq.next_to(fixes, DOWN, buff=0.9)
        new_frame = SurroundingRectangle(new_eq, color=GREEN, buff=0.15, corner_radius=0.1)

        full_fill = self.savings_fill(self.bucket_mob, 0.92)
        self.play(
            Transform(self.fill_mob, full_fill),
            Write(new_eq),
            run_time=1.5,
            rate_func=smooth,
        )
        self.play(Create(new_frame), run_time=0.8)
        self.wait(3.0)  # key insight

        self.fix_grp = VGroup(fixes, new_eq, new_frame, cap, plug, cross)

    # -------------------------------------------------------------------- beat 5
    def beat_insight(self):
        # The one line worth remembering (YELLOW = key insight, RULE 2).
        line1 = Text("The bucket was never the problem.", font_size=42, color=INK)
        line2 = Text("The holes were.", font_size=48, color=YELLOW)
        VGroup(line1, line2).arrange(DOWN, buff=0.4).move_to([0, -0.15, 0])
        box = BackgroundRectangle(
            VGroup(line1, line2), color=BLACK, fill_opacity=0.7, buff=0.35
        )

        # Dim everything else so the sentence owns the frame (RULE 3 hierarchy).
        self.play(
            *[m.animate.set_opacity(0.18) for m in self.fix_grp],
            FadeIn(box),
            run_time=1.0,
        )
        self.play(Write(line1), run_time=1.1)
        self.wait(1.5)  # full sentence
        self.play(FadeIn(line2, shift=UP * 0.15), run_time=0.8)
        self.wait(3.0)  # key insight

        # Close on the takeaway, nothing new added.
        self.play(
            FadeOut(box),
            FadeOut(line1),
            line2.animate.scale(0.85).move_to([0, 0, 0]),
            *[m.animate.set_opacity(0.0) for m in self.fix_grp],
            FadeOut(self.fill_mob),
            FadeOut(self.bucket_mob),
            FadeOut(self.level_lbl),
            FadeOut(self.income_grp),
            FadeOut(self.title),
            run_time=1.3,
        )
        self.wait(2.0)
