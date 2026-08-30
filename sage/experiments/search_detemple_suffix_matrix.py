"""并行运行多个确定性 E12 后缀搜索配置并汇总非证明结果。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter, sleep

from jsonschema import Draft202012Validator
from sage.version import version as sage_version

from euclid_min.formats import load_profile
from experiments.build_detemple_1991_improved import DEFAULT_PROFILE
from experiments.search_detemple_suffix import SAGE_IMAGE


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = (
    Path(__file__).resolve().parent
    / "configs"
    / "e12-suffix-restart-matrix-v1.json"
)
DEFAULT_CONFIG_SCHEMA = (
    REPOSITORY_ROOT
    / "schemas"
    / "suffix-restart-matrix-config-v1.schema.json"
)
DEFAULT_SUMMARY_SCHEMA = (
    REPOSITORY_ROOT
    / "schemas"
    / "suffix-restart-matrix-summary-v1.schema.json"
)
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "e12-suffix-restart-matrix-sage-10.7.json"
)
DEFAULT_RUN_DIRECTORY = (
    REPOSITORY_ROOT / "benchmarks" / "e12-suffix-restart-matrix-sage-10.7"
)
CHILD_SCRIPT = Path(__file__).resolve().parent / "search_detemple_suffix.py"


def load_and_validate(path: Path, schema_path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)
    return data


def effective_config(config: dict, smoke: bool) -> dict:
    if not smoke:
        return config
    result = dict(config)
    result["id"] = f'{config["id"]}-smoke'
    result["max_total_score"] = 13
    result["max_parallel_runs"] = 2
    result["runs"] = [
        {
            **run,
            "beam_width": 1,
            "candidate_width": 2,
            "workers": 2,
            "state_timeout_seconds": 2.0,
        }
        for run in config["runs"]
    ]
    return result


def child_command(
    config: dict,
    run: dict,
    *,
    profile_path: Path,
    summary_path: Path,
    candidate_path: Path,
) -> list[str]:
    command = [
        sys.executable,
        str(CHILD_SCRIPT),
        "--prefix-last-id",
        config["prefix_last_id"],
        "--max-total-score",
        str(config["max_total_score"]),
        "--beam-width",
        str(run["beam_width"]),
        "--candidate-width",
        str(run["candidate_width"]),
        "--workers",
        str(run["workers"]),
        "--state-timeout-seconds",
        str(run["state_timeout_seconds"]),
        "--max-input-level",
        str(run["max_input_level"]),
        "--candidate-strategy",
        run["candidate_strategy"],
        "--heuristic",
        run["heuristic"],
        "--profile",
        str(profile_path),
        "--summary-output",
        str(summary_path),
        "--output",
        str(candidate_path),
        "--write-candidate",
    ]
    if run.get("complexity_order", False):
        command.append("--complexity-order")
    return command


def compact_stats(summary: dict | None) -> dict | None:
    if summary is None:
        return None
    stats = summary["stats"]
    return {
        key: stats[key]
        for key in (
            "expanded_states",
            "generated_candidates",
            "accepted_states",
            "heuristic_evaluations",
            "candidate_prefilter_evaluations",
            "candidate_timeouts",
            "elapsed_seconds",
        )
    }


def portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def run_matrix(
    config: dict,
    *,
    profile_path: Path,
    run_directory: Path,
    progress=print,
) -> dict:
    run_ids = [run["id"] for run in config["runs"]]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("restart 矩阵中的 run id 必须唯一")
    run_directory.mkdir(parents=True, exist_ok=True)
    profile = load_profile(profile_path)
    started_at = datetime.now(timezone.utc)
    started_clock = perf_counter()
    pending = list(config["runs"])
    running: dict[subprocess.Popen, tuple[dict, Path]] = {}
    rows = []

    try:
        while pending or running:
            while pending and len(running) < config["max_parallel_runs"]:
                run = pending.pop(0)
                summary_path = run_directory / f'{run["id"]}.json'
                candidate_path = (
                    REPOSITORY_ROOT
                    / "candidates"
                    / f'regular-17-18e-{run["id"]}.json'
                )
                if summary_path.exists():
                    summary_path.unlink()
                command = child_command(
                    config,
                    run,
                    profile_path=profile_path,
                    summary_path=summary_path,
                    candidate_path=candidate_path,
                )
                process = subprocess.Popen(
                    command,
                    cwd=REPOSITORY_ROOT,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                running[process] = (run, summary_path)
                progress(
                    json.dumps(
                        {
                            "matrix_event": "run_start",
                            "id": run["id"],
                            "pid": process.pid,
                            "workers": run["workers"],
                        },
                        ensure_ascii=False,
                    )
                )

            finished = [
                process for process in running if process.poll() is not None
            ]
            if not finished:
                sleep(0.2)
                continue
            for process in finished:
                run, summary_path = running.pop(process)
                summary = None
                if summary_path.exists():
                    summary = load_and_validate(
                        summary_path,
                        REPOSITORY_ROOT
                        / "schemas"
                        / "suffix-search-summary-v1.schema.json",
                    )
                expected_exit = summary is not None and (
                    (process.returncode == 0 and summary["status"] == "found")
                    or (
                        process.returncode == 4
                        and summary["status"] in (
                            "state_limit",
                            "heuristic_limit",
                        )
                    )
                )
                run_status = (
                    summary["status"]
                    if summary is not None and expected_exit
                    else "failed"
                )
                row = {
                    "id": run["id"],
                    "parameters": {
                        key: (
                            run.get("complexity_order", False)
                            if key == "complexity_order"
                            else run[key]
                        )
                        for key in (
                            "beam_width",
                            "candidate_width",
                            "workers",
                            "state_timeout_seconds",
                            "max_input_level",
                            "candidate_strategy",
                            "heuristic",
                            "complexity_order",
                        )
                    },
                    "summary_path": portable_path(summary_path),
                    "exit_code": process.returncode,
                    "status": run_status,
                    "found_score": (
                        summary["found_score"] if summary is not None else None
                    ),
                    "stats": compact_stats(summary),
                }
                rows.append(row)
                progress(
                    json.dumps(
                        {
                            "matrix_event": "run_end",
                            "id": run["id"],
                            "exit_code": process.returncode,
                            "status": run_status,
                        },
                        ensure_ascii=False,
                    )
                )
    except BaseException:
        for process in running:
            process.terminate()
        for process in running:
            process.wait()
        raise

    rows.sort(key=lambda row: run_ids.index(row["id"]))
    failed_runs = sum(row["status"] == "failed" for row in rows)
    found_runs = sum(row["status"] == "found" for row in rows)
    completed_rows = [
        row
        for row in rows
        if row["status"] != "failed" and row["stats"] is not None
    ]
    aggregate_keys = (
        "expanded_states",
        "generated_candidates",
        "accepted_states",
        "heuristic_evaluations",
        "candidate_prefilter_evaluations",
        "candidate_timeouts",
    )
    status = (
        "found"
        if found_runs
        else "partial_failure" if failed_runs else "complete_no_hit"
    )
    return {
        "schema": "euclid-min-suffix-restart-matrix-summary/v1",
        "mode": "heuristic_nonproof",
        "matrix_id": config["id"],
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "wall_elapsed_seconds": perf_counter() - started_clock,
        "environment": {
            "sage_version": sage_version,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "docker_image": SAGE_IMAGE,
        },
        "profile": {
            "id": profile.data["id"],
            "sha256": profile.sha256,
        },
        "prefix_last_id": config["prefix_last_id"],
        "max_total_score": config["max_total_score"],
        "max_parallel_runs": config["max_parallel_runs"],
        "planned_worker_capacity": sum(
            sorted(
                (run["workers"] for run in config["runs"]),
                reverse=True,
            )[: config["max_parallel_runs"]]
        ),
        "status": status,
        "aggregate": {
            "planned_runs": len(config["runs"]),
            "completed_runs": len(completed_rows),
            "failed_runs": failed_runs,
            "found_runs": found_runs,
            **{
                key: sum(row["stats"][key] for row in completed_rows)
                for key in aggregate_keys
            },
            "summed_run_elapsed_seconds": sum(
                row["stats"]["elapsed_seconds"] for row in completed_rows
            ),
        },
        "runs": rows,
        "interpretation_boundary": (
            "各 run 都使用浮点预筛、beam 截断、层级门和超时；"
            "矩阵未命中不构成 18 E 不存在的证明。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--run-directory", type=Path, default=DEFAULT_RUN_DIRECTORY
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="只跑一层、每 run 两个候选，用于验证调度和产物格式",
    )
    args = parser.parse_args()

    config = load_and_validate(args.config, DEFAULT_CONFIG_SCHEMA)
    config = effective_config(config, args.smoke)
    summary = run_matrix(
        config,
        profile_path=args.profile,
        run_directory=args.run_directory,
        progress=lambda line: print(line, file=sys.stderr, flush=True),
    )
    schema = json.loads(DEFAULT_SUMMARY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] != "partial_failure" else 2


if __name__ == "__main__":
    raise SystemExit(main())
