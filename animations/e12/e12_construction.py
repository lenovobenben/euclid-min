"""The verified twelve-move construction, rendered with Manim Community."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
from manim import (
    Arc, Circle, Create, Dot, FadeIn, FadeOut, Indicate, Line,
    MovingCameraScene, Text, Transform, VGroup, Write, config,
    DOWN, LEFT, RIGHT, UP,
)


DATA_PATH = Path(__file__).with_name("geometry.json")
FONT = os.environ.get("EUCLID_MIN_FONT", "Noto Sans CJK SC")
BACKGROUND = "#07101F"
FOREGROUND = "#E8F0F7"
MUTED = "#8397A8"
BLUE = "#56B4D3"
LINE_BLUE = "#8AC6D9"
GOLD = "#FFC857"
TARGET = "#5DE2A5"
PINK = "#FF7A90"
MAGENTA = "#F45BFF"
STROKE_SCALE = 2 / 3
LABEL_DIRECTIONS = {
    "O": DOWN + RIGHT, "A": RIGHT + DOWN, "ggb_C": LEFT + DOWN,
    "ggb_D": UP + LEFT, "ggb_E": DOWN + LEFT, "ggb_F": DOWN + LEFT,
    "ggb_G": UP + LEFT, "ggb_H": UP + RIGHT, "ggb_I": DOWN + RIGHT,
    "ggb_J": UP + LEFT, "ggb_K": DOWN + LEFT, "ggb_L": UP + RIGHT,
    "ggb_M": DOWN + RIGHT, "ggb_N": UP + RIGHT, "ggb_O": DOWN + LEFT,
    "ggb_P": UP + RIGHT, "ggb_Q": UP + RIGHT, "ggb_R": DOWN + RIGHT,
}


def position(point) -> np.ndarray:
    return np.array([float(point[0]), float(point[1]), 0.0])


class E12Construction(MovingCameraScene):
    def construct(self):
        config.background_color = BACKGROUND
        self.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.labels = {}
        self.drawables = {}
        self.retired = set()
        self.default_width = self.camera.frame.width
        self.intro()
        self.setup_geometry()
        for step in self.data["steps"]:
            self.draw_step(step)
        self.finish()

    def text(self, content, **kwargs):
        return Text(content, font=FONT, color=kwargs.pop("color", FOREGROUND), **kwargs)

    def intro(self):
        title = self.text("正十七边形 · 12 E", font_size=60, weight="MEDIUM")
        title.move_to(UP * 1.9)
        subtitle = self.text("用尺规找到初始顶点的两个相邻顶点", font_size=28, color=MUTED)
        subtitle.next_to(title, DOWN, buff=0.35)
        score = self.text("3 条直线  +  9 个圆", font_size=42, color=GOLD)
        score.move_to(DOWN * 0.15)
        rules = self.text("每画一条直线或一个圆记 1 E；交点免费", font_size=24, color=MUTED)
        rules.next_to(score, DOWN, buff=0.45)
        boundary = self.text("精确验证通过 · 尚未证明最小", font_size=22, color=TARGET)
        boundary.next_to(rules, DOWN, buff=0.35)
        self.play(Write(title), FadeIn(subtitle), run_time=1.0)
        self.play(FadeIn(score, shift=UP * 0.15), FadeIn(rules), FadeIn(boundary), run_time=0.8)
        self.wait(1.6)
        self.play(FadeOut(VGroup(title, subtitle, score, rules, boundary)), run_time=0.5)

    @property
    def screen_scale(self):
        return self.camera.frame.width / self.default_width

    def setup_geometry(self):
        self.camera.frame.set(width=5.8).move_to(LEFT * 0.2)
        self.counter = self.text("00 / 12", font_size=36, color=GOLD, weight="MEDIUM")
        self.counter.set_stroke(BACKGROUND, width=6, background=True).set_z_index(30)
        self.counter_width = self.counter.width

        def pin_counter(counter):
            counter.set(width=self.counter_width * self.screen_scale)
            counter.move_to(self.camera.frame.get_corner(UP + RIGHT)
                            + LEFT * (counter.width / 2 + 0.3 * self.screen_scale)
                            + DOWN * (counter.height / 2 + 0.25 * self.screen_scale))

        self.counter.add_updater(pin_counter)
        self.unit_circle = Circle(radius=1, color=MAGENTA, stroke_width=2.7 * STROKE_SCALE).set_z_index(2)
        self.play(Create(self.unit_circle), FadeIn(self.counter), run_time=0.9)
        self.show_points(0)
        self.wait(0.7)

    def make_point(self, point_id):
        point = self.data["points"][point_id]
        target = point_id in {"ggb_Q", "ggb_R"}
        color = TARGET if target else FOREGROUND
        dot = Dot(position(point["xy"]), radius=0.035 * self.screen_scale, color=color)
        label = self.text(point["label"], font_size=20 if target else 17, color=color)
        label_width = label.width
        direction = LABEL_DIRECTIONS[point_id]

        def pin_label(group):
            group[0].set(width=(0.105 if target else 0.07) * self.screen_scale)
            group[1].set(width=label_width * self.screen_scale)
            group[1].next_to(group[0], direction, buff=0.07 * self.screen_scale)

        group = VGroup(dot, label).set_z_index(12)
        group.add_updater(pin_label)
        group.update()
        return group

    def show_points(self, e_move):
        appearing = []
        for point_id, point in self.data["points"].items():
            if point["birth"] != e_move:
                continue
            group = self.make_point(point_id)
            self.labels[point_id] = group
            appearing.append(FadeIn(group))
        if appearing:
            self.play(*appearing, run_time=0.38 if e_move == 12 else 0.24)

    def move_camera(self, step):
        x0, y0, x1, y1 = map(float, step["frame"])
        # Keep the whole current circle and its definition points in frame.
        # A minimum width avoids jitter between the smaller constructions.
        width = max(5.8, x1 - x0, (y1 - y0) * 16 / 9) * 1.04
        center = np.array([(x0 + x1) / 2, (y0 + y1) / 2, 0])
        if abs(width - self.camera.frame.width) > 0.15 or np.linalg.norm(center - self.camera.frame.get_center()) > 0.2:
            self.play(self.camera.frame.animate.set(width=width).move_to(center), run_time=0.65)

    def marker(self, point_id, color):
        return VGroup(
            Circle(radius=0.12 * self.screen_scale, color=color, stroke_width=2.5 * STROKE_SCALE),
            Dot(radius=0.045 * self.screen_scale, color=color),
        ).move_to(position(self.data["points"][point_id]["xy"])).set_z_index(20)

    def references(self, step):
        first, second = step["refs"]
        markers = VGroup(self.marker(first, PINK if step["op"] == "circle" else GOLD),
                         self.marker(second, GOLD))
        if step["op"] == "circle":
            markers.add(Line(position(self.data["points"][first]["xy"]),
                             position(self.data["points"][second]["xy"]),
                             color=PINK, stroke_width=1.8 * STROKE_SCALE).set_z_index(18))
        self.play(FadeIn(markers), run_time=0.25)
        return markers

    def drawable(self, step):
        if step["op"] == "line":
            return Line(*[position(point) for point in step["ends"]], color=GOLD, stroke_width=2.7 * STROKE_SCALE)
        center = position(step["center"])
        through = position(self.data["points"][step["refs"][1]]["xy"])
        # Rotate the path's starting point to the given point: the compass
        # visibly starts on the known circumference point, with no new geometry.
        angle = math.atan2(*(through - center)[[1, 0]])
        return Circle(radius=float(step["radius"]), color=GOLD, stroke_width=2.7 * STROKE_SCALE
                      ).rotate(angle).move_to(center)

    def counter_animation(self, e_move):
        replacement = self.text(f"{e_move:02d} / 12", font_size=36, color=GOLD, weight="MEDIUM")
        replacement.scale(self.screen_scale).move_to(self.counter)
        replacement.set_stroke(BACKGROUND, width=6, background=True).set_z_index(30)
        return Transform(self.counter, replacement)

    def draw_step(self, step):
        e_move = step["e"]
        if e_move == 12:
            self.play(*[obj.animate.set_stroke(opacity=0.12) for obj in self.drawables.values()],
                      self.unit_circle.animate.set_stroke(width=3.2 * STROKE_SCALE), run_time=0.45)
        self.move_camera(step)
        markers = self.references(step)
        shape = self.drawable(step)
        self.play(Create(shape), self.counter_animation(e_move), run_time=1.2 if e_move == 12 else 0.85)
        self.drawables[step["id"]] = shape
        self.play(FadeOut(markers), run_time=0.18)
        self.show_points(e_move)
        self.wait(0.55 if e_move == 12 else 0.22)
        retiring = [key for key, point in self.data["points"].items()
                    if point["lastUse"] == e_move and key not in {"O", "A", "ggb_Q", "ggb_R"}
                    and key in self.labels and key not in self.retired]
        animations = [FadeOut(self.labels[key]) for key in retiring]
        self.retired.update(retiring)
        if e_move < 12:
            animations.append(shape.animate.set_stroke(color=BLUE if step["op"] == "circle" else LINE_BLUE,
                                                       width=1.35 * STROKE_SCALE, opacity=0.32))
        if animations:
            self.play(*animations, run_time=0.2)

    def finish(self):
        cleanup = [shape.animate.set_stroke(opacity=0.06) for shape in self.drawables.values()]
        cleanup += [FadeOut(group) for key, group in self.labels.items()
                    if key not in {"O", "A", "ggb_Q", "ggb_R"} and key not in self.retired]
        self.play(*cleanup, run_time=0.6)
        self.play(self.camera.frame.animate.set(width=4.9).move_to(RIGHT * 0.05), run_time=1.0)
        origin = position(self.data["points"]["O"]["xy"])
        start = position(self.data["points"]["A"]["xy"])
        upper = position(self.data["points"]["ggb_Q"]["xy"])
        lower = position(self.data["points"]["ggb_R"]["xy"])
        rays = VGroup(*[Line(origin, point, color=TARGET, stroke_width=2.4 * STROKE_SCALE)
                        for point in (start, upper, lower)])
        theta = math.atan2(upper[1], upper[0])
        arcs = VGroup(*[Arc(radius=0.48, start_angle=0, angle=sign * theta,
                           arc_center=origin, color=TARGET, stroke_width=3 * STROKE_SCALE)
                        for sign in (1, -1)])
        formula = self.text("∠AOB₊ = ∠B₋OA = 2π / 17", font_size=22, color=TARGET)
        formula.scale(self.screen_scale).move_to(DOWN * 1.22)
        self.play(Create(rays), Create(arcs), FadeIn(formula),
                  Indicate(self.labels["ggb_Q"][0], color=TARGET),
                  Indicate(self.labels["ggb_R"][0], color=TARGET), run_time=1.2)
        self.wait(3)
        # Credits are separate from the counted construction. No other edges or
        # vertices are drawn: the task ends at the two exact adjacent vertices.
        geometry = [obj for obj in self.mobjects if obj is not self.counter]
        self.counter.clear_updaters()
        self.play(*[FadeOut(obj) for obj in geometry], FadeOut(self.counter), run_time=0.6)
        self.camera.frame.set(width=self.default_width).move_to(np.zeros(3))
        credits = VGroup(
            self.text("12 E · 精确验证通过", font_size=43, color=GOLD),
            self.text("几何主体：QQ 讨论组提供的 GGB 文件，原作者未确认", font_size=21, color=MUTED),
            self.text("Euclid-Min：交点分支改写、证书、独立核验与动画", font_size=21, color=MUTED),
            self.text("已验证上界；尚未证明全局最小", font_size=22, color=TARGET),
            self.text("github.com/lenovobenben/euclid-min", font_size=19, color=MUTED),
        ).arrange(DOWN, buff=0.4)
        self.play(FadeIn(credits), run_time=0.7)
        self.wait(3)
