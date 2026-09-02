"""从 69E 证书提取可精确重放、按输入状态计价的几何 gadget。"""

from __future__ import annotations

from cyclotomic_replay import Circle, CyclotomicReplayer, Line, Point
from proof_hints import build_proof_hints


def _references(entry: dict) -> list[str]:
    if entry["op"] == "line":
        return list(entry["through"])
    if entry["op"] == "circle":
        return [entry["center"], entry["through"]]
    if entry["op"] == "intersect":
        return list(entry["objects"])
    raise ValueError(f"未知证书操作: {entry['op']}")


def _program_slice(program: list[dict], first_e: int, last_e: int) -> list[dict]:
    if not (1 <= first_e <= last_e):
        raise ValueError("gadget 的 E 区间无效")
    result = []
    current_e = 0
    for entry in program:
        if entry["op"] != "intersect":
            current_e += 1
            if current_e > last_e:
                break
        if first_e <= current_e <= last_e:
            result.append(entry)
    paid = sum(entry["op"] != "intersect" for entry in result)
    if paid != last_e - first_e + 1:
        raise ValueError("gadget 程序片段没有覆盖完整 E 区间")
    return result


def _prefix_replayer(
    program: list[dict],
    first_e: int,
    hints: dict[str, Point],
) -> CyclotomicReplayer:
    """精确重放到 first_e 之前，并保留该前缀的全部具名状态。"""

    replayer = CyclotomicReplayer()
    current_e = 0
    for entry in program:
        if entry["op"] != "intersect":
            if current_e + 1 == first_e:
                break
            replayer.execute(entry)
            current_e += 1
        else:
            replayer.bind_witness(entry, hints[entry["id"]])
    if current_e != first_e - 1:
        raise ValueError(f"无法重放到 {first_e - 1}E 前缀")
    return replayer


def _full_replayer(
    program: list[dict],
    hints: dict[str, Point],
) -> CyclotomicReplayer:
    replayer = CyclotomicReplayer()
    for entry in program:
        if entry["op"] == "intersect":
            replayer.bind_witness(entry, hints[entry["id"]])
        else:
            replayer.execute(entry)
    return replayer


def _boundary_inputs(
    fragment: list[dict],
    all_names: dict[str, object],
) -> tuple[list[str], list[str]]:
    local_names = set()
    points: list[str] = []
    drawables: list[str] = []
    seen_points = set()
    seen_drawables = set()
    for entry in fragment:
        for reference in _references(entry):
            if reference in local_names:
                continue
            value = all_names[reference]
            if isinstance(value, Point):
                if reference not in seen_points:
                    points.append(reference)
                    seen_points.add(reference)
            elif isinstance(value, (Line, Circle)):
                if reference not in seen_drawables:
                    drawables.append(reference)
                    seen_drawables.add(reference)
            else:
                raise TypeError(f"边界引用 {reference} 不是点或可画对象")
        local_names.add(entry["id"])
    return points, drawables


def _macro_by_id(ga_ir: dict, macro_id: str) -> dict:
    matches = [
        macro
        for macro in ga_ir["baseline_macro_partition"]
        if macro["id"] == macro_id
    ]
    if len(matches) != 1:
        raise ValueError(f"GA-IR 中宏 {macro_id} 不是唯一记录")
    return matches[0]


def extract_baseline_gadget(
    certificate: dict,
    ga_ir: dict,
    *,
    gadget_id: str,
    macro_id: str,
    all_names: dict[str, object] | None = None,
    hints: dict[str, Point] | None = None,
) -> dict:
    """提取一个宏，并在其原始前缀状态上精确执行和动态计价。"""

    macro = _macro_by_id(ga_ir, macro_id)
    first_e = macro["first_e_move"]
    last_e = macro["last_e_move"]
    program = certificate["construction"]["program"]
    fragment = _program_slice(program, first_e, last_e)
    if hints is None:
        hints = build_proof_hints()
    if all_names is None:
        all_names = _full_replayer(program, hints).names
    input_points, input_drawables = _boundary_inputs(
        fragment,
        all_names,
    )

    representations = ga_ir["representations"]
    input_representations = sorted(
        representation["id"]
        for representation in representations
        if representation["symbol"] in macro["input_symbols"]
        and representation["available_e_move"] < first_e
    )
    output_representations = list(macro["output_representations"])
    represented_output_symbols = {
        representation["symbol"]
        for representation in representations
        if representation["id"] in output_representations
    }
    if not set(macro["output_symbols"]) <= represented_output_symbols:
        missing = set(macro["output_symbols"]) - represented_output_symbols
        raise ValueError(f"宏 {macro_id} 的输出没有全部几何物化: {sorted(missing)}")

    replayer = _prefix_replayer(program, first_e, hints)
    duplicate_paid_drawables = []
    new_drawables = []
    bound_points = []
    lines = 0
    circles = 0
    for entry in fragment:
        if entry["op"] == "intersect":
            replayer.bind_witness(entry, hints[entry["id"]])
            bound_points.append(entry["id"])
            continue
        old_drawables = [*replayer.lines, *replayer.circles]
        replayer.execute(entry)
        drawable = replayer.names[entry["id"]]
        if any(
            type(old) is type(drawable) and old == drawable
            for old in old_drawables
        ):
            duplicate_paid_drawables.append(entry["id"])
        new_drawables.append(entry["id"])
        if entry["op"] == "line":
            lines += 1
        else:
            circles += 1
    if replayer.e_move != last_e:
        raise ValueError(f"gadget {gadget_id} 重放后不是 {last_e}E")
    if duplicate_paid_drawables:
        raise ValueError(
            f"gadget {gadget_id} 重画既有对象: {duplicate_paid_drawables}"
        )
    if new_drawables != macro["paid_drawables"]:
        raise ValueError(f"gadget {gadget_id} 与 GA-IR 宏对象不一致")

    transitions = ga_ir["transitions"][first_e - 1 : last_e]
    free_points = [
        point_id
        for transition in transitions
        for point_id in transition["free_points_born"]
    ]
    if len(free_points) != len(set(free_points)):
        raise ValueError(f"gadget {gadget_id} 的免费闭包增量含重复点")
    declared_ids = {entry["id"] for entry in fragment}
    if not set(bound_points) <= declared_ids:
        raise AssertionError("gadget 免费绑定没有包含在程序片段中")

    return {
        "id": gadget_id,
        "status": "verified_in_baseline_prefix_state",
        "source_macro": macro_id,
        "context": {
            "before_e_move": first_e - 1,
            "after_e_move": last_e,
            "state_policy": "all_prefix_traces_persist",
        },
        "algebraic_interface": {
            "input_symbols": list(macro["input_symbols"]),
            "output_symbols": list(macro["output_symbols"]),
            "input_representations": input_representations,
            "output_representations": output_representations,
        },
        "geometric_interface": {
            "required_points": input_points,
            "required_drawables": input_drawables,
        },
        "program": fragment,
        "effects": {
            "new_paid_drawables": new_drawables,
            "explicit_points_bound": bound_points,
            "full_free_closure_delta": {
                "point_count": len(free_points),
                "point_ids": free_points,
            },
        },
        "cost": {
            "metric": "contextual_distinct_new_drawables",
            "e_move": len(new_drawables),
            "lines": lines,
            "circles": circles,
            "duplicate_drawables": len(duplicate_paid_drawables),
        },
        "verification": {
            "exact_prefix_replay": True,
            "exact_fragment_replay": True,
            "all_boundary_references_available": True,
            "all_declared_intersection_branches_verified": True,
            "all_output_representations_verified_by_ga_ir": True,
        },
    }


def build_tail_gadget_library(certificate: dict, ga_ir: dict, source: dict) -> dict:
    program = certificate["construction"]["program"]
    # 周期 proof hints 和完整名字空间在两个 gadget 之间共享。否则每新增一个
    # gadget 都会重复构造整套分圆周期，生成耗时会不必要地线性增长。
    hints = build_proof_hints()
    all_names = _full_replayer(program, hints).names
    gadgets = [
        extract_baseline_gadget(
            certificate,
            ga_ir,
            gadget_id="gadget.low-tail-9e",
            macro_id="macro.low-tail",
            all_names=all_names,
            hints=hints,
        ),
        extract_baseline_gadget(
            certificate,
            ga_ir,
            gadget_id="gadget.high-tail-9e",
            macro_id="macro.high-tail",
            all_names=all_names,
            hints=hints,
        ),
    ]
    low, high = gadgets
    shared_points = sorted(
        set(low["geometric_interface"]["required_points"])
        & set(high["geometric_interface"]["required_points"])
    )
    shared_drawables = sorted(
        set(low["geometric_interface"]["required_drawables"])
        & set(high["geometric_interface"]["required_drawables"])
    )
    shared_input_representations = sorted(
        set(low["algebraic_interface"]["input_representations"])
        & set(high["algebraic_interface"]["input_representations"])
    )
    all_new_drawables = [
        drawable
        for gadget in gadgets
        for drawable in gadget["effects"]["new_paid_drawables"]
    ]
    if len(all_new_drawables) != len(set(all_new_drawables)):
        raise ValueError("两个尾部 gadget 在基线中含重名付费对象")
    return {
        "schema": "euclid-min-geometry-gadget-library/v1",
        "source": source,
        "semantics": {
            "gadget": "named_geometry_program_with_explicit_state_boundary",
            "cost": "distinct_new_drawables_after_exact_execution_in_input_state",
            "free_effect": "all_finite_real_intersections_added_after_each_paid_draw",
            "scope": "verified_baseline_prefix_context_not_context_free_fixed_price",
        },
        "gadgets": gadgets,
        "comparison": {
            "baseline_combined_cost_e": sum(
                gadget["cost"]["e_move"] for gadget in gadgets
            ),
            "baseline_distinct_new_drawables": len(all_new_drawables),
            "shared_required_points": shared_points,
            "shared_required_drawables": shared_drawables,
            "shared_input_representations": shared_input_representations,
            "optimization_target": "jointly_compile_both_tail_interfaces_below_18E",
            "minimality_claim": "none",
        },
        "limitations": [
            "9E 是每个 gadget 在原始前缀状态中的观测成本，不是脱离状态的固定单价。",
            "当前库只收录视频基线实现，尚未枚举等价代数改写或替代几何程序。",
            "两个 gadget 的联合优化必须重新执行对象去重和免费交点闭包，不能直接相加候选报价。",
        ],
    }
