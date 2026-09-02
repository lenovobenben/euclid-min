"""正 257 边形 69E 构造的精确语义依赖超图。

点可以由多对已画对象产生，同一个付费对象也可能由多组已知点画出。这里枚举证书
全部具名点与全部既有付费对象之间的精确关联，再用单调前向闭包排除循环自证。
"""

from __future__ import annotations

from itertools import combinations

from cyclotomic_replay import Circle, CyclotomicReplayer, Line, Point
from proof_hints import build_proof_hints


def _paid_definition(entry: dict) -> list[str]:
    if entry["op"] == "line":
        return list(entry["through"])
    if entry["op"] == "circle":
        return [entry["center"], entry["through"]]
    raise ValueError(f"不是付费对象: {entry['op']}")


def _pair_present(pairs: list[list[str]], expected: list[str], ordered: bool) -> bool:
    if ordered:
        return expected in pairs
    expected_set = set(expected)
    return any(set(pair) == expected_set for pair in pairs)


def exact_replay_universe(certificate: dict):
    program = certificate["construction"]["program"]
    hints = build_proof_hints()
    replayer = CyclotomicReplayer()
    point_items: list[tuple[str, Point]] = [
        ("B", replayer.names["B"]),
        ("C", replayer.names["C"]),
    ]
    drawable_items = [("c0", replayer.names["c0"])]
    entries_by_id: dict[str, dict] = {}
    program_indices = {"B": 0, "C": 0, "c0": 0}
    paid_entries: list[dict] = []
    point_entries: list[dict] = []
    for program_index, entry in enumerate(program, start=1):
        name = entry["id"]
        entries_by_id[name] = entry
        program_indices[name] = program_index
        if entry["op"] == "intersect":
            witness = hints[name]
            replayer.bind_witness(entry, witness)
            point_items.append((name, witness))
            point_entries.append(entry)
        else:
            replayer.execute(entry)
            drawable = replayer.names[name]
            if not isinstance(drawable, (Line, Circle)):
                raise AssertionError(f"{name} 不是可画对象")
            drawable_items.append((name, drawable))
            paid_entries.append(entry)
    return {
        "program": program,
        "replayer": replayer,
        "point_items": point_items,
        "drawable_items": drawable_items,
        "entries_by_id": entries_by_id,
        "program_indices": program_indices,
        "paid_entries": paid_entries,
        "point_entries": point_entries,
    }


def _assert_unique_geometry(items: list[tuple[str, object]], label: str) -> None:
    for index, (name, value) in enumerate(items):
        aliases = [
            old_name
            for old_name, old_value in items[:index]
            if type(old_value) is type(value) and old_value == value
        ]
        if aliases:
            raise ValueError(
                f"{label} {name} 与既有名字 {', '.join(aliases)} 重合"
            )


def _first_paid_consumers(replay: dict) -> dict[str, dict | None]:
    consumers: dict[str, dict | None] = {
        name: None for name, _point in replay["point_items"]
    }
    e_move = 0
    for program_index, entry in enumerate(replay["program"], start=1):
        if entry["op"] == "intersect":
            continue
        e_move += 1
        for reference in _paid_definition(entry):
            if reference in consumers and consumers[reference] is None:
                consumers[reference] = {
                    "id": entry["id"],
                    "program_index": program_index,
                    "e_move": e_move,
                }
    return consumers


def _available_pairs(
    incident_names: list[str],
    drawable_values: dict[str, object],
) -> list[list[str]]:
    result = []
    for first, second in combinations(incident_names, 2):
        first_value = drawable_values[first]
        second_value = drawable_values[second]
        if (
            type(first_value) is type(second_value)
            and first_value == second_value
        ):
            continue
        result.append([first, second])
    return result


def _build_hypergraph(certificate: dict) -> dict:
    replay = exact_replay_universe(certificate)
    point_items = replay["point_items"]
    drawable_items = replay["drawable_items"]
    _assert_unique_geometry(point_items, "点")
    _assert_unique_geometry(drawable_items, "作图对象")

    point_values = dict(point_items)
    drawable_values = dict(drawable_items)
    program_indices = replay["program_indices"]
    consumers = _first_paid_consumers(replay)
    end_program_index = len(replay["program"]) + 1

    # 共享一次精确关联矩阵，避免在点生产边和对象定义边中重复做分圆域运算。
    incident_drawables: dict[str, list[str]] = {}
    incident_points: dict[str, list[str]] = {
        name: [] for name, _drawable in drawable_items
    }
    for point_name, point in point_items:
        incident = []
        for drawable_name, drawable in drawable_items:
            if drawable.contains(point):
                incident.append(drawable_name)
                incident_points[drawable_name].append(point_name)
        incident_drawables[point_name] = incident

    point_records = []
    for entry in replay["point_entries"]:
        name = entry["id"]
        declared_pair = list(entry["objects"])
        incident = incident_drawables[name]
        original_cutoff = program_indices[name]
        consumer = consumers[name]
        pre_use_cutoff = (
            consumer["program_index"] if consumer else end_program_index
        )

        def producers_before(cutoff: int) -> list[list[str]]:
            available = [
                drawable_name
                for drawable_name in incident
                if program_indices[drawable_name] < cutoff
            ]
            return _available_pairs(available, drawable_values)

        original_producers = producers_before(original_cutoff)
        pre_use_producers = producers_before(pre_use_cutoff)
        final_producers = _available_pairs(incident, drawable_values)
        for scope, pairs in (
            ("原绑定时刻", original_producers),
            ("首次付费使用前", pre_use_producers),
            ("最终状态", final_producers),
        ):
            if not _pair_present(pairs, declared_pair, ordered=False):
                raise ValueError(f"点 {name} 的声明来源未出现在{scope}")
        point_records.append(
            {
                "id": name,
                "e_move": replay["replayer"].bound_point_e_moves[name],
                "program_index": original_cutoff,
                "declared_producer": declared_pair,
                "first_paid_consumer": consumer,
                "incident_drawables_in_final_state": incident,
                "producers_at_declared_binding": original_producers,
                "producers_before_first_paid_use": pre_use_producers,
                "producers_in_final_state": final_producers,
            }
        )

    drawable_records = []
    e_move = 0
    for entry in replay["paid_entries"]:
        e_move += 1
        name = entry["id"]
        drawable = drawable_values[name]
        declared = _paid_definition(entry)
        if isinstance(drawable, Line):
            definitions = [
                [first, second]
                for first, second in combinations(incident_points[name], 2)
                if point_values[first] != point_values[second]
            ]
            ordered = False
        elif isinstance(drawable, Circle):
            centers = [
                point_name
                for point_name, point in point_items
                if point == drawable.center
            ]
            through_points = [
                point_name
                for point_name in incident_points[name]
                if point_values[point_name] != drawable.center
            ]
            definitions = [
                [center, through]
                for center in centers
                for through in through_points
            ]
            ordered = True
        else:
            raise AssertionError(f"{name} 的类型无效")
        if not _pair_present(definitions, declared, ordered=ordered):
            raise ValueError(f"对象 {name} 的声明定义不在精确定义超边中")
        drawable_records.append(
            {
                "id": name,
                "e_move": e_move,
                "program_index": program_indices[name],
                "kind": entry["op"],
                "declared_definition": declared,
                "incident_named_points": incident_points[name],
                "exact_named_point_definitions": definitions,
            }
        )

    return {
        "points": point_records,
        "drawables": drawable_records,
        "initial_points": ["B", "C"],
        "initial_drawables": ["c0"],
        "target_witnesses": certificate["assertions"]["target_witnesses"],
    }


def forward_closure(hypergraph: dict, selected_paid: set[str]) -> dict:
    """在禁止循环自证的单调语义下计算可构造闭包。"""

    available_points = set(hypergraph["initial_points"])
    available_drawables = set(hypergraph["initial_drawables"])
    while True:
        old_size = (len(available_points), len(available_drawables))
        for point in hypergraph["points"]:
            if point["id"] in available_points:
                continue
            if any(
                first in available_drawables and second in available_drawables
                for first, second in point["producers_in_final_state"]
            ):
                available_points.add(point["id"])
        for drawable in hypergraph["drawables"]:
            if (
                drawable["id"] not in selected_paid
                or drawable["id"] in available_drawables
            ):
                continue
            if any(
                first in available_points and second in available_points
                for first, second in drawable["exact_named_point_definitions"]
            ):
                available_drawables.add(drawable["id"])
        if old_size == (len(available_points), len(available_drawables)):
            break
    reached_witnesses = [
        pair
        for pair in hypergraph["target_witnesses"]
        if all(point in available_points for point in pair)
    ]
    return {
        "available_points": available_points,
        "available_drawables": available_drawables,
        "reached_target_witnesses": reached_witnesses,
        "target_reached": bool(reached_witnesses),
    }


def analyze_semantic_dependencies(certificate: dict, source: dict) -> dict:
    """枚举语义超边并证明给定对象宇宙内的单步删除均失败。"""

    hypergraph = _build_hypergraph(certificate)
    paid_ids = [item["id"] for item in hypergraph["drawables"]]
    full = forward_closure(hypergraph, set(paid_ids))
    if not full["target_reached"]:
        raise ValueError("完整 69E 对象集合未能在语义超图中到达目标")

    target_point_ids = list(
        dict.fromkeys(
            point
            for pair in hypergraph["target_witnesses"]
            for point in pair
        )
    )
    deletion_trials = []
    for drawable in hypergraph["drawables"]:
        removed = drawable["id"]
        result = forward_closure(hypergraph, set(paid_ids) - {removed})
        deletion_trials.append(
            {
                "removed": removed,
                "e_move": drawable["e_move"],
                "target_reached": result["target_reached"],
                "reached_named_points": len(result["available_points"]),
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
    all_individually_necessary = not removable
    minimum = len(paid_ids) if all_individually_necessary else None

    point_edges = sum(
        len(item["producers_in_final_state"])
        for item in hypergraph["points"]
    )
    definition_edges = sum(
        len(item["exact_named_point_definitions"])
        for item in hypergraph["drawables"]
    )
    report = {
        "schema": "euclid-min-regular-257-semantic-dependency-report/v1",
        "source": source,
        "semantics": {
            "point_universe": "initial_and_named_certificate_points",
            "drawable_universe": "initial_circle_and_69_verified_paid_drawables",
            "scheduling": "monotone_forward_closure_with_paid_draw_reordering",
            "cycle_policy": "an_object_or_point_must_be_available_before_it_is_used",
            "limitations": [
                "不引入证书 69 个付费对象以外的新直线或新圆。",
                "对象的替代定义只使用证书中的具名点，不枚举未命名自动交点。",
                "结论是给定对象与具名点宇宙内的相对不可删性，不是 69E 的全局下界。",
            ],
        },
        "summary": {
            "initial_points": len(hypergraph["initial_points"]),
            "named_intersection_points": len(hypergraph["points"]),
            "unique_named_points": (
                len(hypergraph["initial_points"]) + len(hypergraph["points"])
            ),
            "initial_drawables": len(hypergraph["initial_drawables"]),
            "paid_drawables": len(hypergraph["drawables"]),
            "point_producer_hyperedges": point_edges,
            "points_with_multiple_final_producers": sum(
                len(item["producers_in_final_state"]) > 1
                for item in hypergraph["points"]
            ),
            "points_with_multiple_producers_at_declared_binding": sum(
                len(item["producers_at_declared_binding"]) > 1
                for item in hypergraph["points"]
            ),
            "points_with_multiple_producers_before_first_paid_use": sum(
                len(item["producers_before_first_paid_use"]) > 1
                for item in hypergraph["points"]
            ),
            "drawable_definition_hyperedges": definition_edges,
            "drawables_with_multiple_named_definitions": sum(
                len(item["exact_named_point_definitions"]) > 1
                for item in hypergraph["drawables"]
            ),
            "single_deletion_trials": len(deletion_trials),
            "individually_removable_paid_draws": len(removable),
        },
        "hypergraph": hypergraph,
        "full_universe_closure": {
            "target_reached": full["target_reached"],
            "reached_named_points": len(full["available_points"]),
            "reached_drawables": len(full["available_drawables"]),
            "reached_target_witnesses": full["reached_target_witnesses"],
        },
        "single_deletion_trials": deletion_trials,
        "irreducibility_result": {
            "method": "monotone_single_deletion_exhaustion",
            "all_paid_draws_individually_necessary": all_individually_necessary,
            "removable_paid_draws": removable,
            "minimum_required_paid_draws_within_universe": minimum,
            "required_paid_draws": paid_ids if all_individually_necessary else [],
            "proof_argument": (
                "可构造闭包关于允许使用的付费对象集合单调。若删除任意一个对象后，"
                "即使保留其余全部对象仍不能到达目标，则任何更小子集也不能到达"
                "目标；因此本对象与具名点宇宙内的最小值为 69。"
            ),
        },
    }
    return report
