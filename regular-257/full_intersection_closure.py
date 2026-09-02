"""现有 70 个对象的完整有限实交点闭包与相对不可删性审计。"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from math import comb
from typing import Callable

from cyclotomic_replay import (
    FIELD,
    ORDER_FIELD,
    Circle,
    Line,
    Point,
)
from semantic_dependency import exact_replay_universe


Trace = Callable[[str], None]


@dataclass
class _ArrangementPoint:
    point: Point | None
    incident_drawables: set[str] = field(default_factory=set)
    names: list[str] = field(default_factory=list)
    origin: str = ""


def _point_key(point: Point):
    """统一主域与 UCF 表示，使相同精确点具有相同哈希键。"""

    try:
        return ("FIELD", FIELD(point.x), FIELD(point.y))
    except (TypeError, ValueError):
        return ("UCF", ORDER_FIELD(point.x), ORDER_FIELD(point.y))


def _line_line_point(first: Line, second: Line) -> Point | None:
    determinant = first.a * second.b - second.a * first.b
    if determinant == 0:
        return None
    return Point(
        (first.b * second.c - second.b * first.c) / determinant,
        (first.c * second.a - second.c * first.a) / determinant,
    )


def _line_circle_count(
    a,
    b,
    c,
    circle: Circle,
) -> int:
    """不求根，只精确判断直线与圆有几个有限实交点。"""

    norm_squared = a * a + b * b
    signed = a * circle.center.x + b * circle.center.y + c
    discriminant = circle.radius_squared * norm_squared - signed * signed
    ordered = ORDER_FIELD(discriminant)
    if ordered < 0:
        return 0
    if ordered == 0:
        return 1
    return 2


def _circle_circle_count(first: Circle, second: Circle) -> int:
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    if dx == 0 and dy == 0:
        return 0
    return _line_circle_count(
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared,
        first,
    )


def _radical_axis(first: Circle, second: Circle):
    dx = second.center.x - first.center.x
    dy = second.center.y - first.center.y
    if dx == 0 and dy == 0:
        return None
    return (
        2 * dx,
        2 * dy,
        first.center.x * first.center.x
        + first.center.y * first.center.y
        - first.radius_squared
        - second.center.x * second.center.x
        - second.center.y * second.center.y
        + second.radius_squared,
    )


def _homogeneous_intersection(first, second):
    first_a, first_b, first_c = first
    second_a, second_b, second_c = second
    w = first_a * second_b - second_a * first_b
    if w == 0:
        return None
    return (
        first_b * second_c - second_b * first_c,
        first_c * second_a - second_c * first_a,
        w,
    )


def _homogeneous_on_circle(point, circle: Circle) -> bool:
    x, y, w = point
    dx = x - circle.center.x * w
    dy = y - circle.center.y * w
    return dx * dx + dy * dy == circle.radius_squared * w * w


def _coincident_lines(first, second) -> bool:
    first_a, first_b, first_c = first
    second_a, second_b, second_c = second
    return (
        first_a * second_b == second_a * first_b
        and first_a * second_c == second_a * first_c
        and first_b * second_c == second_b * first_c
    )


def _affine_point(homogeneous) -> Point:
    x, y, w = homogeneous
    return Point(x / w, y / w)


def _drawable_definition(entry: dict) -> list[str]:
    if entry["op"] == "line":
        return list(entry["through"])
    if entry["op"] == "circle":
        return [entry["center"], entry["through"]]
    raise ValueError(f"不是付费对象: {entry['op']}")


def _build_arrangement(
    certificate: dict,
    trace: Trace | None = None,
    include_runtime_points: bool = False,
) -> dict:
    replay = exact_replay_universe(certificate)
    drawable_items = replay["drawable_items"]
    point_items = replay["point_items"]
    drawable_values = dict(drawable_items)
    drawable_order = {name: index for index, (name, _value) in enumerate(drawable_items)}
    lines = [
        (name, value)
        for name, value in drawable_items
        if isinstance(value, Line)
    ]
    circles = [
        (name, value)
        for name, value in drawable_items
        if isinstance(value, Circle)
    ]

    records: list[_ArrangementPoint] = []
    records_by_key: dict[tuple, _ArrangementPoint] = {}

    def add_coordinate_point(
        point: Point,
        incident: tuple[str, str],
        origin: str,
    ) -> _ArrangementPoint:
        key = _point_key(point)
        record = records_by_key.get(key)
        if record is None:
            record = _ArrangementPoint(point=point, origin=origin)
            records_by_key[key] = record
            records.append(record)
        record.incident_drawables.update(incident)
        return record

    line_pairs = list(combinations(lines, 2))
    line_line_intersection_count = 0
    for pair_index, ((first_name, first), (second_name, second)) in enumerate(
        line_pairs,
        start=1,
    ):
        point = _line_line_point(first, second)
        if point is not None:
            line_line_intersection_count += 1
            add_coordinate_point(
                point,
                (first_name, second_name),
                "line_line",
            )
        if trace and pair_index % 500 == 0:
            trace(f"line_line_pairs={pair_index}/{len(line_pairs)}")

    # 先把直线交点与全部 5 个圆做关联，捕获至少两条直线经过的曲线交点。
    for record in records:
        if record.point is None:
            continue
        for circle_name, circle in circles:
            if circle.contains(record.point):
                record.incident_drawables.add(circle_name)

    # 圆—圆分支不直接开平方。根轴交点可定位所有经过既有直线或第三个圆的分支；
    # 完全孤立的剩余分支按精确实交点计数建立抽象点。
    circle_pair_counts: dict[tuple[str, str], int] = {}
    for (first_name, first), (second_name, second) in combinations(circles, 2):
        circle_pair_counts[(first_name, second_name)] = _circle_circle_count(
            first,
            second,
        )

    # 三圆公共点由两条根轴的交点唯一确定。若根轴重合，则三个圆同轴并共享两个
    # 分支；当前 5 个圆不存在这种退化，显式拒绝可防止错误拆分抽象分支。
    for triple in combinations(circles, 3):
        (first_name, first), (second_name, second), (third_name, third) = triple
        first_axis = _radical_axis(first, second)
        second_axis = _radical_axis(first, third)
        if first_axis is None or second_axis is None:
            continue
        homogeneous = _homogeneous_intersection(first_axis, second_axis)
        if homogeneous is None:
            if _coincident_lines(first_axis, second_axis):
                raise ValueError(
                    f"暂不支持同轴三圆: {first_name}/{second_name}/{third_name}"
                )
            continue
        if not _homogeneous_on_circle(homogeneous, first):
            continue
        point = _affine_point(homogeneous)
        record = add_coordinate_point(
            point,
            (first_name, second_name),
            "circle_triple",
        )
        record.incident_drawables.add(third_name)
        for line_name, line in lines:
            if line.contains(point):
                record.incident_drawables.add(line_name)
        for circle_name, circle in circles:
            if circle.contains(point):
                record.incident_drawables.add(circle_name)

    for (first_name, first), (second_name, second) in combinations(circles, 2):
        axis = _radical_axis(first, second)
        if axis is None:
            continue
        coincident_drawn_lines: list[str] = []
        for line_name, line in lines:
            line_coefficients = (line.a, line.b, line.c)
            homogeneous = _homogeneous_intersection(line_coefficients, axis)
            if homogeneous is None:
                if _coincident_lines(line_coefficients, axis):
                    coincident_drawn_lines.append(line_name)
                continue
            if not _homogeneous_on_circle(homogeneous, first):
                continue
            point = _affine_point(homogeneous)
            record = add_coordinate_point(
                point,
                (first_name, second_name),
                "circle_circle_on_line",
            )
            record.incident_drawables.add(line_name)
            for circle_name, circle in circles:
                if circle.contains(point):
                    record.incident_drawables.add(circle_name)

        existing_count = sum(
            first_name in record.incident_drawables
            and second_name in record.incident_drawables
            for record in records
        )
        residual = circle_pair_counts[(first_name, second_name)] - existing_count
        if residual < 0 or residual > 2:
            raise ValueError(
                f"圆 {first_name}/{second_name} 的残余分支计数无效: {residual}"
            )
        for record in records:
            if (
                first_name in record.incident_drawables
                and second_name in record.incident_drawables
            ):
                record.incident_drawables.update(coincident_drawn_lines)
        for _branch in range(residual):
            records.append(
                _ArrangementPoint(
                    point=None,
                    incident_drawables={
                        first_name,
                        second_name,
                        *coincident_drawn_lines,
                    },
                    origin="circle_circle_residual",
                )
            )

    line_circle_counts: dict[tuple[str, str], int] = {}
    for line_index, (line_name, line) in enumerate(lines, start=1):
        for circle_name, circle in circles:
            pair = (line_name, circle_name)
            total_count = _line_circle_count(line.a, line.b, line.c, circle)
            line_circle_counts[pair] = total_count
            already_materialized = sum(
                line_name in record.incident_drawables
                and circle_name in record.incident_drawables
                for record in records
            )
            residual = total_count - already_materialized
            if residual < 0 or residual > 2:
                raise ValueError(
                    f"{line_name}/{circle_name} 的残余交点计数无效: {residual}"
                )
            for _branch in range(residual):
                records.append(
                    _ArrangementPoint(
                        point=None,
                        incident_drawables={line_name, circle_name},
                        origin="line_circle_residual",
                    )
                )
        if trace and line_index % 10 == 0:
            trace(f"line_circle_rows={line_index}/{len(lines)}")

    # 把 83 个具名点映射到安排点；正常情况下全部已有精确坐标记录。
    for name, point in point_items:
        key = _point_key(point)
        record = records_by_key.get(key)
        if record is None:
            incident = {
                drawable_name
                for drawable_name, drawable in drawable_items
                if drawable.contains(point)
            }
            candidates = [
                candidate
                for candidate in records
                if candidate.point is None
                and candidate.incident_drawables == incident
                and not candidate.names
            ]
            if not candidates:
                raise ValueError(
                    f"具名点 {name} 无法映射到无坐标残余交点"
                )
            # 两个孤立分支可能具有完全相同的对象关联。它们在闭包语义中对称，
            # 按稳定发现顺序分配具名标签即可，不需要浮点坐标区分。
            record = candidates[0]
        if record.names:
            raise ValueError(
                f"具名点 {name} 与 {', '.join(record.names)} 坐标重复"
            )
        record.names.append(name)

    # 具名点优先使用原名，其余点按稳定发现顺序编号。
    point_records = []
    unnamed_index = 0
    record_ids: dict[int, str] = {}
    for record in records:
        if record.names:
            point_id = record.names[0]
        else:
            unnamed_index += 1
            point_id = f"U{unnamed_index:04d}"
        record_ids[id(record)] = point_id
        incident = sorted(
            record.incident_drawables,
            key=lambda name: drawable_order[name],
        )
        point_records.append(
            {
                "id": point_id,
                "names": record.names,
                "origin": record.origin,
                "incident_drawables": incident,
                "producer_pair_count": comb(len(incident), 2),
            }
        )

    points_by_drawable = {
        name: [
            point["id"]
            for point in point_records
            if name in point["incident_drawables"]
        ]
        for name, _drawable in drawable_items
    }
    name_to_id = {
        name: point["id"]
        for point in point_records
        for name in point["names"]
    }

    drawable_records = []
    e_move = 0
    entries_by_id = replay["entries_by_id"]
    for name, drawable in drawable_items[1:]:
        e_move += 1
        entry = entries_by_id[name]
        incident_points = points_by_drawable[name]
        if isinstance(drawable, Line):
            condition = {
                "kind": "two_incident_points",
                "incident_points": incident_points,
                "definition_count": comb(len(incident_points), 2),
            }
        elif isinstance(drawable, Circle):
            center_ids = [
                name_to_id[point_name]
                for point_name, point in point_items
                if point == drawable.center
            ]
            through_ids = [
                point_id
                for point_id in incident_points
                if point_id not in center_ids
            ]
            if not center_ids or not through_ids:
                raise ValueError(f"圆 {name} 缺少完整交点闭包定义")
            condition = {
                "kind": "center_and_incident_point",
                "center_points": center_ids,
                "through_points": through_ids,
                "definition_count": len(center_ids) * len(through_ids),
            }
        else:
            raise AssertionError(f"{name} 不是可画对象")
        declared_names = _drawable_definition(entry)
        declared_ids = [name_to_id[point_name] for point_name in declared_names]
        drawable_records.append(
            {
                "id": name,
                "e_move": e_move,
                "kind": entry["op"],
                "declared_definition": declared_ids,
                "condition": condition,
            }
        )

    raw_intersection_count = (
        line_line_intersection_count
        + sum(line_circle_counts.values())
        + sum(circle_pair_counts.values())
    )
    result = {
        "points": point_records,
        "drawables": drawable_records,
        "initial_points": [name_to_id["B"], name_to_id["C"]],
        "initial_drawables": ["c0"],
        "target_witnesses": [
            [name_to_id[first], name_to_id[second]]
            for first, second in certificate["assertions"]["target_witnesses"]
        ],
        "raw_intersection_count": raw_intersection_count,
        "line_line_pairs": len(line_pairs),
        "line_circle_pairs": len(lines) * len(circles),
        "circle_circle_pairs": comb(len(circles), 2),
    }
    if include_runtime_points:
        named_values = dict(point_items)
        result["_runtime_point_values"] = {
            record_ids[id(record)]: (
                record.point
                if record.point is not None
                else named_values[record.names[0]]
                if record.names
                else None
            )
            for record in records
        }
        result["_runtime_drawable_values"] = drawable_values
    return result


def build_runtime_arrangement(
    certificate: dict,
    trace: Trace | None = None,
) -> dict:
    """构造带临时精确坐标对象的完整安排；该运行时字段不写入 JSON。"""

    return _build_arrangement(
        certificate,
        trace=trace,
        include_runtime_points=True,
    )


def forward_full_closure(arrangement: dict, selected_paid: set[str]) -> dict:
    """在完整交点安排上做禁止循环自证的单调前向闭包。"""

    available_points = set(arrangement["initial_points"])
    available_drawables = set(arrangement["initial_drawables"])
    while True:
        old_size = (len(available_points), len(available_drawables))
        for point in arrangement["points"]:
            if point["id"] in available_points:
                continue
            if (
                sum(
                    name in available_drawables
                    for name in point["incident_drawables"]
                )
                >= 2
            ):
                available_points.add(point["id"])
        for drawable in arrangement["drawables"]:
            name = drawable["id"]
            if name not in selected_paid or name in available_drawables:
                continue
            condition = drawable["condition"]
            if condition["kind"] == "two_incident_points":
                ready = (
                    sum(
                        point in available_points
                        for point in condition["incident_points"]
                    )
                    >= 2
                )
            else:
                ready = any(
                    point in available_points
                    for point in condition["center_points"]
                ) and any(
                    point in available_points
                    for point in condition["through_points"]
                )
            if ready:
                available_drawables.add(name)
        if old_size == (len(available_points), len(available_drawables)):
            break
    reached_witnesses = [
        pair
        for pair in arrangement["target_witnesses"]
        if all(point in available_points for point in pair)
    ]
    return {
        "available_points": available_points,
        "available_drawables": available_drawables,
        "reached_target_witnesses": reached_witnesses,
        "target_reached": bool(reached_witnesses),
    }


def analyze_full_intersection_closure(
    certificate: dict,
    source: dict,
    trace: Trace | None = None,
) -> dict:
    arrangement = _build_arrangement(certificate, trace=trace)
    paid_ids = [item["id"] for item in arrangement["drawables"]]
    full = forward_full_closure(arrangement, set(paid_ids))
    if not full["target_reached"]:
        raise ValueError("完整对象集合未能在全交点闭包中到达目标")

    target_point_ids = list(
        dict.fromkeys(
            point
            for pair in arrangement["target_witnesses"]
            for point in pair
        )
    )
    deletion_trials = []
    for drawable in arrangement["drawables"]:
        removed = drawable["id"]
        result = forward_full_closure(arrangement, set(paid_ids) - {removed})
        deletion_trials.append(
            {
                "removed": removed,
                "e_move": drawable["e_move"],
                "target_reached": result["target_reached"],
                "reached_points": len(result["available_points"]),
                "reached_drawables": len(result["available_drawables"]),
                "available_target_points": [
                    name
                    for name in target_point_ids
                    if name in result["available_points"]
                ],
            }
        )
    removable = [
        trial["removed"] for trial in deletion_trials if trial["target_reached"]
    ]
    all_necessary = not removable
    total_point_producers = sum(
        point["producer_pair_count"] for point in arrangement["points"]
    )
    total_definitions = sum(
        drawable["condition"]["definition_count"]
        for drawable in arrangement["drawables"]
    )
    points = arrangement["points"]
    report_arrangement = {
        key: value
        for key, value in arrangement.items()
        if key != "raw_intersection_count"
    }
    return {
        "schema": "euclid-min-regular-257-full-intersection-closure-report/v1",
        "source": source,
        "semantics": {
            "point_universe": "all_finite_real_intersections_of_the_70_existing_drawables",
            "drawable_universe": "initial_circle_and_69_verified_paid_drawables",
            "scheduling": "monotone_forward_closure_with_paid_draw_reordering",
            "cycle_policy": "an_object_or_point_must_be_available_before_it_is_used",
            "limitations": [
                "不引入现有 69 个付费对象以外的新直线或新圆。",
                "结论是固定对象宇宙内的相对不可删性，不是 69E 的全局下界。",
            ],
        },
        "summary": {
            "drawable_pairs": (
                arrangement["line_line_pairs"]
                + arrangement["line_circle_pairs"]
                + arrangement["circle_circle_pairs"]
            ),
            "line_line_pairs": arrangement["line_line_pairs"],
            "line_circle_pairs": arrangement["line_circle_pairs"],
            "circle_circle_pairs": arrangement["circle_circle_pairs"],
            "raw_intersection_count": arrangement["raw_intersection_count"],
            "unique_finite_real_points": len(points),
            "named_points": sum(bool(point["names"]) for point in points),
            "unnamed_points": sum(not point["names"] for point in points),
            "point_producer_pairs": total_point_producers,
            "drawable_definition_pairs": total_definitions,
            "single_deletion_trials": len(deletion_trials),
            "individually_removable_paid_draws": len(removable),
        },
        "arrangement": report_arrangement,
        "full_closure": {
            "target_reached": full["target_reached"],
            "reached_points": len(full["available_points"]),
            "reached_drawables": len(full["available_drawables"]),
            "reached_target_witnesses": full["reached_target_witnesses"],
        },
        "single_deletion_trials": deletion_trials,
        "irreducibility_result": {
            "method": "full_intersection_monotone_single_deletion_exhaustion",
            "all_paid_draws_individually_necessary": all_necessary,
            "removable_paid_draws": removable,
            "minimum_required_paid_draws_within_fixed_object_universe": (
                len(paid_ids) if all_necessary else None
            ),
            "required_paid_draws": paid_ids if all_necessary else [],
            "proof_argument": (
                "已把现有 70 个对象的全部有限实交点纳入点宇宙，并允许 69 个付费"
                "对象用其中任意合法点组重新定义和任意重排。闭包关于允许对象集合"
                "单调；若删除任一对象并保留其余全部对象仍不能到达目标，则任何"
                "更小子集也不能到达目标。"
            ),
        },
    }
