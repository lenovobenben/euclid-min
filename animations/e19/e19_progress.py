"""Euclid-Min 19 E 构造演示动画。"""

from __future__ import annotations

import json
import math
from pathlib import Path

from manim import (
    Arc,
    Arrow,
    Circle,
    Create,
    Dot,
    FadeIn,
    FadeOut,
    GrowFromCenter,
    Line,
    MovingCameraScene,
    Restore,
    Text,
    Transform,
    VGroup,
    Write,
    config,
    DOWN,
    LEFT,
    RIGHT,
    UP,
)


DATA_PATH = Path(__file__).with_name("geometry.json")
FONT = "Noto Sans CJK SC"

BACKGROUND = "#07101F"
FOREGROUND = "#E8F0F7"
MUTED = "#8397A8"
GUIDE = "#557086"
CIRCLE_BLUE = "#56B4D3"
LINE_BLUE = "#8AC6D9"
GOLD = "#FFC857"
TARGET = "#5DE2A5"
ALERT = "#FF7A90"
TARGET_CIRCLE = "#F45BFF"

# 第 19 步必须同时看见定直线的两个已知点 Q、P，以及直线与单位圆新切出的 B。
# 最终结论再缩回单位圆全景，避免局部放大把 Q 裁出画面。
TARGET_LINE_FRAME_CENTER = (-0.04, 0.18)
TARGET_LINE_FRAME_WIDTH = 7.6
FINAL_OVERVIEW_FRAME_CENTER = (0.0, 0.0)
FINAL_OVERVIEW_FRAME_WIDTH = 10.8

# 正片不再为文字面板预留空间，几何图占满整个画面。
# 直线先按最大镜头范围生成，再由相机裁切。这样临时缩远时，直线仍会穿过
# 位于旧默认画幅之外的定位点（第 4 步的上下两个定线点尤其如此）。
LOGICAL_BOUNDS = (-3.6, 3.6, -2.0, 2.0)
GEOMETRY_SCALE = 2.72
GEOMETRY_SHIFT = DOWN * 0.12

KEY_LABELS = {
    "O": ("O", DOWN + LEFT),
    "A": ("A", DOWN + RIGHT),
    "Q": ("Q", DOWN + LEFT),
    "Qhalf": ("Q′", DOWN),
    "Qquarter": ("Q″", DOWN),
    "M1_2": ("M₁,₂", DOWN),
    "M0_2": ("M₀,₂", DOWN),
    "H0_4": ("H₀,₄", UP),
    "H1_4": ("H₁,₄", DOWN),
    "Y": ("Y", RIGHT),
    "M0_4": ("M₀,₄", UP + RIGHT),
    "H4_8": ("H₄,₈", DOWN),
    "target_helper_point": ("P", UP + LEFT),
}


def logical_to_scene(point: list[float] | tuple[float, float]):
    return GEOMETRY_SHIFT + RIGHT * (point[0] * GEOMETRY_SCALE) + UP * (
        point[1] * GEOMETRY_SCALE
    )


def clipped_line(geometry: dict) -> tuple[list[float], list[float]]:
    a, b, c = geometry["a"], geometry["b"], geometry["c"]
    x_min, x_max, y_min, y_max = LOGICAL_BOUNDS
    candidates: list[tuple[float, float]] = []

    if abs(b) > 1e-10:
        for x in (x_min, x_max):
            y = (-a * x - c) / b
            if y_min - 1e-8 <= y <= y_max + 1e-8:
                candidates.append((x, y))
    if abs(a) > 1e-10:
        for y in (y_min, y_max):
            x = (-b * y - c) / a
            if x_min - 1e-8 <= x <= x_max + 1e-8:
                candidates.append((x, y))

    unique: list[tuple[float, float]] = []
    for point in candidates:
        if not any(math.dist(point, other) < 1e-8 for other in unique):
            unique.append(point)
    if len(unique) < 2:
        raise ValueError(f"line does not cross viewport: {geometry}")
    pair = max(
        ((first, second) for first in unique for second in unique if first != second),
        key=lambda item: math.dist(*item),
    )
    return list(pair[0]), list(pair[1])


class E19Progress(MovingCameraScene):
    def construct(self):
        config.background_color = BACKGROUND
        self.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.drawn_objects = VGroup()
        self.drawable_by_id: dict[str, Line | Circle] = {}
        self.point_objects: dict[str, VGroup] = {}

        self.play_intro()
        self.setup_construction()
        self.play_construction()
        self.highlight_target()

    def make_text(self, content: str, **kwargs) -> Text:
        return Text(content, font=FONT, color=kwargs.pop("color", FOREGROUND), **kwargs)

    def play_intro(self) -> None:
        title = self.make_text(
            "用尺规找到正十七边形的相邻顶点",
            font_size=48,
            weight="MEDIUM",
        )
        title.move_to(UP * 2.25)
        explanation = self.make_text(
            "每画一条直线或一个圆，记 1 E",
            font_size=25,
            color=MUTED,
        )
        explanation.next_to(title, DOWN, buff=0.32)

        old_score = self.make_text("项目基线 32 E", font_size=50, color=MUTED)
        new_score = self.make_text("当前证书 19 E", font_size=62, color=GOLD, weight="MEDIUM")
        scores = VGroup(old_score, new_score).arrange(RIGHT, buff=2.0)
        scores.move_to(DOWN * 0.1)
        arrow = Arrow(
            old_score.get_right() + RIGHT * 0.18,
            new_score.get_left() + LEFT * 0.18,
            color=CIRCLE_BLUE,
            stroke_width=5,
            buff=0,
        )
        saving = self.make_text("减少 13 E", font_size=31, color=TARGET, weight="MEDIUM")
        saving.next_to(scores, DOWN, buff=0.72)

        self.play(Write(title), FadeIn(explanation, shift=UP * 0.08), run_time=1.0)
        self.play(FadeIn(old_score), run_time=0.45)
        self.play(Create(arrow), GrowFromCenter(new_score), run_time=0.8)
        self.play(FadeIn(saving, shift=UP * 0.1), run_time=0.45)
        self.wait(1.4)
        self.play(
            FadeOut(VGroup(title, explanation, old_score, arrow, new_score, saving)),
            run_time=0.55,
        )

    def setup_construction(self) -> None:
        self.counter = self.make_text(
            "00 / 19",
            font_size=42,
            color=GOLD,
            weight="MEDIUM",
        )
        self.counter.to_corner(UP + RIGHT, buff=0.34)
        self.counter.set_stroke(BACKGROUND, width=7, background=True)
        self.counter.set_z_index(10)
        self.default_frame_width = self.camera.frame.width
        self.counter_base_width = self.counter.width

        def pin_counter(counter: Text) -> None:
            frame_scale = self.camera.frame.width / self.default_frame_width
            counter.set(width=self.counter_base_width * frame_scale)
            counter.move_to(
                self.camera.frame.get_corner(UP + RIGHT)
                + LEFT * (counter.width / 2 + 0.3 * frame_scale)
                + DOWN * (counter.height / 2 + 0.22 * frame_scale)
            )

        self.counter.add_updater(pin_counter)

        initial = self.data["initial"]
        self.unit_circle = Circle(
            radius=initial["unit_circle"]["radius"] * GEOMETRY_SCALE,
            color=TARGET_CIRCLE,
            stroke_width=3.2,
            fill_opacity=0,
        ).set_stroke(opacity=0.92)
        self.unit_circle.move_to(logical_to_scene(initial["unit_circle"]["center"]))

        self.play(
            FadeIn(self.counter),
            Create(self.unit_circle),
            run_time=0.75,
        )
        self.show_point("O", immediate=False)
        self.show_point("A", immediate=False)
        self.play(
            FadeIn(self.point_objects["O"]),
            FadeIn(self.point_objects["A"]),
            run_time=0.4,
        )
        self.wait(0.25)
        self.camera.frame.save_state()

    def make_drawable(self, event: dict):
        if event["op"] == "line":
            start, end = clipped_line(event["geometry"])
            return Line(
                logical_to_scene(start),
                logical_to_scene(end),
                color=GOLD,
                stroke_width=3.2,
            )
        geometry = event["geometry"]
        circle = Circle(
            radius=geometry["radius"] * GEOMETRY_SCALE,
            color=GOLD,
            stroke_width=3.2,
            fill_opacity=0,
        )
        circle.move_to(logical_to_scene(geometry["center"]))
        return circle

    def show_point(self, point_id: str, immediate: bool = True) -> None:
        if point_id in self.point_objects:
            return
        label_text, direction = KEY_LABELS[point_id]
        point = self.data["points"][point_id]
        dot = Dot(logical_to_scene(point), radius=0.042, color=FOREGROUND)
        label = self.make_text(label_text, font_size=15, color=FOREGROUND)
        label.next_to(dot, direction, buff=0.07)
        group = VGroup(dot, label)
        self.point_objects[point_id] = group
        if immediate:
            self.play(FadeIn(group, scale=0.7), run_time=0.14)

    def update_counter(self, e_move: int):
        new_counter = self.make_text(
            f"{e_move:02d} / 19",
            font_size=42,
            color=GOLD,
            weight="MEDIUM",
        )
        new_counter.scale(self.camera.frame.width / self.default_frame_width)
        new_counter.move_to(self.counter)
        new_counter.set_stroke(BACKGROUND, width=7, background=True).set_z_index(10)
        return Transform(self.counter, new_counter)

    def adjust_camera(self, e_move: int) -> None:
        if e_move in {5, 11, 14}:
            self.play(Restore(self.camera.frame), run_time=0.65)
            return
        cues = {
            # 第 4 步的两个定线点在单位圆上下方，必须临时扩大视野。
            4: ((0.0, 0.0), 18.4),
            10: ((-0.28, 0.22), 9.2),
            13: ((-0.12, 0.5), 9.0),
            17: ((0.52, 0.25), 9.2),
            18: ((0.18, 0.12), 7.8),
            19: (TARGET_LINE_FRAME_CENTER, TARGET_LINE_FRAME_WIDTH),
        }
        cue = cues.get(e_move)
        if cue is None:
            return
        center, width = cue
        self.play(
            self.camera.frame.animate.move_to(logical_to_scene(center)).set(width=width),
            run_time=0.68,
        )

    def reference_marker(self, point_id: str, color: str) -> VGroup:
        position = logical_to_scene(self.data["points"][point_id])
        marker = VGroup(
            Circle(
                radius=0.115,
                color=color,
                stroke_width=3.4,
                fill_opacity=0,
            ).move_to(position),
            Dot(position, radius=0.048, color=color),
        )
        marker.set_z_index(8)
        return marker

    def show_references(self, event: dict) -> VGroup:
        if event["op"] == "line":
            first_id, second_id = event["through"]
            overlay = VGroup(
                self.reference_marker(first_id, GOLD),
                self.reference_marker(second_id, GOLD),
            )
        else:
            center_id = event["center"]
            through_id = event["through"]
            center = logical_to_scene(self.data["points"][center_id])
            through = logical_to_scene(self.data["points"][through_id])
            radius_guide = Line(
                center,
                through,
                color=ALERT,
                stroke_width=2.4,
            ).set_z_index(7)
            overlay = VGroup(
                radius_guide,
                self.reference_marker(center_id, ALERT),
                self.reference_marker(through_id, GOLD),
            )
        self.play(FadeIn(overlay, scale=0.72), run_time=0.22)
        return overlay

    def play_construction(self) -> None:
        for event in self.data["events"]:
            if event["kind"] == "intersection":
                if event["id"] in KEY_LABELS:
                    self.show_point(event["id"])
                continue

            e_move = event["e_move"]
            self.adjust_camera(e_move)
            references = self.show_references(event)
            drawable = self.make_drawable(event)
            self.play(
                Create(drawable),
                self.update_counter(e_move),
                run_time=0.48 if e_move < 18 else 0.8,
            )
            self.drawn_objects.add(drawable)
            self.drawable_by_id[event["id"]] = drawable
            if e_move < 18:
                self.play(
                    drawable.animate.set_stroke(
                        color=CIRCLE_BLUE if event["op"] == "circle" else LINE_BLUE,
                        width=1.55,
                        opacity=0.44,
                    ),
                    FadeOut(references),
                    run_time=0.14,
                )
            elif e_move == 18:
                self.play(
                    drawable.animate.set_stroke(color=ALERT, width=2.5, opacity=0.9),
                    FadeOut(references),
                    run_time=0.18,
                )
            elif e_move == 19:
                self.play(FadeOut(references), run_time=0.18)
                self.wait(0.45)

    def highlight_target(self) -> None:
        target_point = self.data["target"]["point"]
        target_dot = Dot(logical_to_scene(target_point), radius=0.09, color=TARGET)
        target_label = self.make_text("B", font_size=22, color=TARGET, weight="MEDIUM")
        target_label.next_to(target_dot, UP + RIGHT, buff=0.1)
        pulse = Circle(
            radius=0.1,
            color=TARGET,
            stroke_width=3,
            fill_opacity=0,
        ).move_to(target_dot)

        background_draws = VGroup(
            *(
                drawable
                for drawable_id, drawable in self.drawable_by_id.items()
                if drawable_id not in {"target_line", "target_helper_circle"}
            )
        )
        secondary_labels = VGroup(
            *(
                group
                for point_id, group in self.point_objects.items()
                if point_id not in {"O", "A", "Q", "target_helper_point"}
            )
        )
        self.play(
            background_draws.animate.set_stroke(opacity=0.2),
            FadeOut(secondary_labels),
            self.unit_circle.animate.set_stroke(
                color=TARGET_CIRCLE,
                width=4.2,
                opacity=1,
            ),
            run_time=0.55,
        )
        self.play(FadeIn(target_dot, scale=1.8), FadeIn(target_label), run_time=0.35)
        self.play(pulse.animate.scale(5).set_stroke(opacity=0), run_time=0.75)
        self.play(
            self.camera.frame.animate.move_to(
                logical_to_scene(FINAL_OVERVIEW_FRAME_CENTER)
            ).set(width=FINAL_OVERVIEW_FRAME_WIDTH),
            run_time=0.8,
        )

        origin = logical_to_scene(self.data["initial"]["O"])
        start = logical_to_scene(self.data["initial"]["A"])
        target = logical_to_scene(target_point)
        theta = math.atan2(target_point[1], target_point[0])
        oa_ray = Line(origin, start, color=TARGET, stroke_width=3.4)
        ob_ray = Line(origin, target, color=TARGET, stroke_width=3.4)
        angle_arc = Arc(
            radius=0.43 * GEOMETRY_SCALE,
            start_angle=0,
            angle=theta,
            arc_center=origin,
            color=TARGET,
            stroke_width=5,
        )
        angle_label = self.make_text(
            "∠AOB = 2π / 17",
            font_size=15,
            color=TARGET,
            weight="MEDIUM",
        )
        angle_label.move_to(
            origin
            + RIGHT * (0.72 * GEOMETRY_SCALE)
            + DOWN * 0.48
        )
        self.play(
            Create(oa_ray),
            Create(ob_ray),
            Create(angle_arc),
            FadeIn(angle_label),
            run_time=0.85,
        )
        self.wait(3.0)
