from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sage.all import AA
from jsonschema import Draft202012Validator

from euclid_min.geometry import Line, Point
from euclid_min.replay import ProgramReplayer
from euclid_min.search import (
    BoundedBreadthFirstSearch,
    DeterministicBeamSearch,
    OneMoveTargetHeuristic,
    ParallelHeuristicBeamSearch,
    PointGoal,
    PointDistanceHeuristic,
    Regular17CandidateHeuristic,
    Regular17Heuristic,
    Regular17OneMoveHeuristic,
    SearchNode,
    generate_candidates,
)
from euclid_min.search.export import build_program_from_steps
from euclid_min.search.candidates import generate_prefiltered_candidates
from euclid_min.search.checkpoint import load_checkpoint, save_checkpoint
from euclid_min.search.index import ExactStateIndex, state_fingerprint, states_equal
from euclid_min.search.parallel_beam import _ordered_indexed_candidates
from euclid_min.target import TargetName, adjacent_targets
from experiments.search_detemple_suffix import exact_prefix


class CandidateGenerationTests(unittest.TestCase):
    def test_initial_candidates_are_complete_and_deterministic(self):
        candidates = generate_candidates(SearchNode.initial().state)
        self.assertEqual([candidate.op for candidate in candidates], ["line", "circle"])
        self.assertEqual(candidates[0].first, Point(0, 0))
        self.assertEqual(candidates[0].second, Point(1, 0))
        self.assertEqual(candidates[1].first, Point(1, 0))
        self.assertEqual(candidates[1].second, Point(0, 0))

    def test_diverse_prefilter_retains_lines_and_circles(self):
        state = SearchNode.initial().state
        heuristic = Regular17CandidateHeuristic()
        heuristic.prepare_state(state)

        candidates, raw_operations, eligible_operations = (
            generate_prefiltered_candidates(
                state,
                limit=4,
                score_operation=heuristic.evaluate_points,
                operation_key=heuristic.operation_key,
                operation_level=heuristic.operation_level,
                exact_deduplicate=False,
                diversify=True,
            )
        )

        self.assertEqual(raw_operations, 3)
        self.assertEqual(eligible_operations, 2)
        self.assertEqual({candidate.op for candidate in candidates}, {"line", "circle"})


class StateIndexTests(unittest.TestCase):
    def test_operation_order_is_removed_only_after_exact_confirmation(self):
        initial = SearchNode.initial()
        candidates = generate_candidates(initial.state)
        line_first = initial.apply(candidates[0])
        circle_first = initial.apply(candidates[1])

        line_then_circle = line_first.apply(
            next(
                candidate
                for candidate in generate_candidates(line_first.state)
                if candidate.op == "circle"
                and candidate.first == Point(1, 0)
                and candidate.second == Point(0, 0)
            )
        )
        circle_then_line = circle_first.apply(
            next(
                candidate
                for candidate in generate_candidates(circle_first.state)
                if candidate.op == "line"
                and candidate.drawable() == candidates[0].drawable()
            )
        )

        self.assertTrue(states_equal(line_then_circle.state, circle_then_line.state))
        self.assertEqual(
            state_fingerprint(line_then_circle.state),
            state_fingerprint(circle_then_line.state),
        )
        index = ExactStateIndex()
        self.assertTrue(index.add_if_better(line_then_circle.state, 2))
        self.assertFalse(index.add_if_better(circle_then_line.state, 2))


class SearchEngineTests(unittest.TestCase):
    def test_rediscovers_equilateral_vertex_in_one_move(self):
        root_three_over_two = AA(3).sqrt() / 2
        goal = PointGoal(Point(AA(1) / 2, root_three_over_two))
        outcome = BoundedBreadthFirstSearch().search(goal, max_score=1)
        self.assertEqual(outcome.status, "found")
        self.assertIsNotNone(outcome.node)
        self.assertEqual(outcome.node.score, 1)
        self.assertEqual(outcome.node.steps[0].op, "circle")

    def test_rediscovers_midpoint_and_exports_replayable_program(self):
        goal = PointGoal(Point(AA(1) / 2, 0))
        outcome = BoundedBreadthFirstSearch().search(
            goal,
            max_score=3,
            max_states=1000,
        )
        self.assertEqual(outcome.status, "found")
        self.assertIsNotNone(outcome.node)
        self.assertEqual(outcome.node.score, 3)

        program, state = build_program_from_steps(outcome.node.steps)
        replay = ProgramReplayer().replay(program)
        self.assertEqual(replay.e_move, 3)
        self.assertTrue(state.contains_point(Point(AA(1) / 2, 0)))

    def test_state_limit_is_reported_without_claiming_exhaustion(self):
        goal = PointGoal(Point(AA(1) / 3, 0))
        outcome = BoundedBreadthFirstSearch().search(
            goal,
            max_score=3,
            max_states=1,
        )
        self.assertEqual(outcome.status, "state_limit")
        self.assertIsNone(outcome.node)
        self.assertTrue(outcome.frontier)

    def test_checkpoint_round_trip_resumes_without_losing_frontier(self):
        midpoint = PointGoal(Point(AA(1) / 2, 0))
        first_run = BoundedBreadthFirstSearch().search(
            midpoint,
            max_score=3,
            max_states=1,
        )
        self.assertEqual(first_run.status, "state_limit")

        repository_root = Path(__file__).resolve().parents[2]
        profile_path = repository_root / "profiles" / "regular-17-e-fixed-v1.yaml"
        with TemporaryDirectory() as temporary_directory:
            checkpoint_path = Path(temporary_directory) / "search.json"
            save_checkpoint(
                checkpoint_path,
                profile_path=profile_path,
                max_score=3,
                frontier=first_run.frontier,
                stats=first_run.stats,
            )
            checkpoint = load_checkpoint(
                checkpoint_path,
                profile_path=profile_path,
            )

        self.assertEqual(checkpoint.max_score, 3)
        self.assertEqual(len(checkpoint.frontier), len(first_run.frontier))
        resumed = BoundedBreadthFirstSearch().search(
            midpoint,
            max_score=checkpoint.max_score,
            max_states=1000,
            initial_frontier=checkpoint.frontier,
        )
        self.assertEqual(resumed.status, "found")
        self.assertEqual(resumed.node.score, 3)

    def test_m4_checkpoint_without_timing_fields_remains_loadable(self):
        goal = PointGoal(Point(AA(1) / 3, 0))
        outcome = BoundedBreadthFirstSearch().search(
            goal,
            max_score=2,
            max_states=1,
        )
        repository_root = Path(__file__).resolve().parents[2]
        profile_path = repository_root / "profiles" / "regular-17-e-fixed-v1.yaml"
        with TemporaryDirectory() as temporary_directory:
            checkpoint_path = Path(temporary_directory) / "m4.json"
            save_checkpoint(
                checkpoint_path,
                profile_path=profile_path,
                max_score=2,
                frontier=outcome.frontier,
                stats=outcome.stats,
            )
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            for key in tuple(data["previous_stats"]):
                if key not in {
                    "expanded_states",
                    "generated_candidates",
                    "accepted_states",
                    "equivalent_pruned",
                    "max_frontier",
                }:
                    del data["previous_stats"][key]
            checkpoint_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            checkpoint = load_checkpoint(
                checkpoint_path,
                profile_path=profile_path,
            )
        self.assertTrue(checkpoint.frontier)
        self.assertEqual(checkpoint.previous_stats.elapsed_seconds, 0.0)


class HeuristicSearchTests(unittest.TestCase):
    def test_target_incidence_score_prefers_an_exact_target_chord(self):
        initial = SearchNode.initial().state
        target = adjacent_targets()[TargetName.B_PLUS]
        chord_state = initial.clone()
        chord_state.add_line(Line(1, 0, -target.x))

        heuristic = Regular17Heuristic()
        self.assertLess(
            heuristic.evaluate(chord_state),
            heuristic.evaluate(initial),
        )

    def test_beam_search_finds_goal_but_never_claims_pruned_exhaustion(self):
        root_three_over_two = AA(3).sqrt() / 2
        equilateral = Point(AA(1) / 2, root_three_over_two)
        found = DeterministicBeamSearch().search(
            PointGoal(equilateral),
            PointDistanceHeuristic(equilateral),
            max_score=1,
            beam_width=1,
        )
        self.assertEqual(found.status, "found")
        self.assertEqual(found.node.score, 1)

        unreachable = Point(AA(1) / 3, 0)
        limited = DeterministicBeamSearch().search(
            PointGoal(unreachable),
            PointDistanceHeuristic(unreachable),
            max_score=2,
            beam_width=1,
        )
        self.assertEqual(limited.status, "heuristic_limit")
        self.assertGreater(limited.stats.heuristic_pruned, 0)
        self.assertGreater(limited.stats.heuristic_evaluations, 0)
        self.assertGreaterEqual(limited.stats.elapsed_seconds, 0)

    def test_beam_search_can_continue_from_a_scored_exact_prefix(self):
        initial = SearchNode.initial()
        prefix = initial.apply(generate_candidates(initial.state)[1])
        root_three_over_two = AA(3).sqrt() / 2
        equilateral = PointGoal(Point(AA(1) / 2, root_three_over_two))

        outcome = DeterministicBeamSearch().search(
            equilateral,
            PointDistanceHeuristic(*equilateral.points),
            max_score=1,
            beam_width=1,
            initial_node=prefix,
        )

        self.assertEqual(outcome.status, "found")
        self.assertEqual(outcome.node.score, 1)

    def test_beam_candidate_prefilter_limits_exact_expansion(self):
        unreachable = Point(AA(1) / 3, 0)
        outcome = DeterministicBeamSearch().search(
            PointGoal(unreachable),
            PointDistanceHeuristic(unreachable),
            max_score=1,
            beam_width=1,
            candidate_width=1,
            candidate_heuristic=Regular17CandidateHeuristic(),
        )

        self.assertEqual(outcome.status, "heuristic_limit")
        self.assertEqual(outcome.stats.generated_candidates, 1)
        self.assertEqual(outcome.stats.candidate_prefilter_evaluations, 3)
        self.assertEqual(outcome.stats.candidate_prefilter_pruned, 2)

    def test_beam_parallel_expansion_preserves_deterministic_result(self):
        root_three_over_two = AA(3).sqrt() / 2
        equilateral = PointGoal(Point(AA(1) / 2, root_three_over_two))

        serial = DeterministicBeamSearch().search(
            equilateral,
            PointDistanceHeuristic(*equilateral.points),
            max_score=1,
            beam_width=2,
        )
        parallel = ParallelHeuristicBeamSearch().search(
            equilateral,
            PointDistanceHeuristic(*equilateral.points),
            Regular17CandidateHeuristic(),
            max_score=1,
            beam_width=2,
            candidate_width=2,
            workers=2,
            state_timeout_seconds=5,
        )

        self.assertEqual(parallel.status, "found")
        self.assertEqual(parallel.node.steps, serial.node.steps)

    def test_candidate_prefilter_can_reject_deep_input_points(self):
        state = SearchNode.initial().state
        deep_point = Point(AA(2).sqrt(), 0)
        state._add_point(deep_point, level=2)
        heuristic = Regular17CandidateHeuristic(max_input_level=1)
        heuristic.prepare_state(state)

        score = heuristic.evaluate_points(
            "line",
            deep_point,
            state.points[0],
        )

        self.assertIsNone(score)

    def test_candidate_complexity_uses_cached_provenance_cost(self):
        state = SearchNode.initial().state
        algebraic = Point(AA(2).sqrt(), 0)
        state._add_point(algebraic, level=2, complexity=2)
        heuristic = Regular17CandidateHeuristic()
        heuristic.prepare_state(state, include_complexity=True)

        rational_cost = heuristic.operation_complexity(
            "line",
            state.points[0],
            state.points[1],
        )
        algebraic_cost = heuristic.operation_complexity(
            "line",
            state.points[0],
            algebraic,
        )

        self.assertEqual(rational_cost.estimated_complexity, 1)
        self.assertEqual(algebraic_cost.estimated_complexity, 2)
        self.assertLess(rational_cost, algebraic_cost)

    def test_complexity_scheduler_preserves_original_candidate_indices(self):
        candidates = generate_candidates(SearchNode.initial().state)

        ordered = _ordered_indexed_candidates(candidates, (2, 1))

        self.assertEqual([index for index, _candidate in ordered], [1, 0])

    def test_one_move_heuristic_detects_a_target_bearing_point_pair(self):
        target = adjacent_targets()[TargetName.B_PLUS]
        state = SearchNode.initial().state
        baseline = Regular17OneMoveHeuristic().evaluate(state)

        enriched = state.clone()
        enriched._add_point(Point(target.x, 1))
        enriched._add_point(Point(target.x, 2))
        improved = OneMoveTargetHeuristic(target).evaluate(enriched)

        self.assertEqual(improved.next_drawable_residual, 0.0)
        self.assertLess(improved, baseline)


class ProfilingArtifactTests(unittest.TestCase):
    def test_repository_profile_matches_its_schema(self):
        repository_root = Path(__file__).resolve().parents[2]
        artifact = json.loads(
            (
                repository_root
                / "benchmarks"
                / "m5-search-profile-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )
        schema = json.loads(
            (
                repository_root / "schemas" / "search-profile-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(artifact)

    def test_suffix_search_summary_matches_its_schema(self):
        repository_root = Path(__file__).resolve().parents[2]
        artifact = json.loads(
            (
                repository_root
                / "benchmarks"
                / "e12-suffix-search-wide-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )
        schema = json.loads(
            (
                repository_root
                / "schemas"
                / "suffix-search-summary-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(artifact)

    def test_suffix_restart_matrix_configs_match_their_schema(self):
        repository_root = Path(__file__).resolve().parents[2]
        schema = json.loads(
            (
                repository_root
                / "schemas"
                / "suffix-restart-matrix-config-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for name in (
            "e12-suffix-restart-matrix-v1.json",
            "e12-suffix-complexity-matrix-v1.json",
        ):
            config = json.loads(
                (
                    repository_root
                    / "sage"
                    / "experiments"
                    / "configs"
                    / name
                ).read_text(encoding="utf-8")
            )
            validator.validate(config)

    def test_suffix_restart_matrix_artifacts_match_their_schemas(self):
        repository_root = Path(__file__).resolve().parents[2]
        matrix_schema = json.loads(
            (
                repository_root
                / "schemas"
                / "suffix-restart-matrix-summary-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        suffix_schema = json.loads(
            (
                repository_root
                / "schemas"
                / "suffix-search-summary-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(matrix_schema)
        matrix_validator = Draft202012Validator(matrix_schema)
        Draft202012Validator.check_schema(suffix_schema)
        suffix_validator = Draft202012Validator(suffix_schema)
        for name in (
            "e12-suffix-restart-matrix-sage-10.7.json",
            "e12-suffix-complexity-matrix-sage-10.7.json",
        ):
            artifact = json.loads(
                (repository_root / "benchmarks" / name).read_text(
                    encoding="utf-8"
                )
            )
            matrix_validator.validate(artifact)
            for run in artifact["runs"]:
                run_artifact = json.loads(
                    (repository_root / run["summary_path"]).read_text(
                        encoding="utf-8"
                    )
                )
                suffix_validator.validate(run_artifact)

    def test_final_attempt_artifacts_record_bounded_no_hit_results(self):
        repository_root = Path(__file__).resolve().parents[2]
        benchmark_root = repository_root / "benchmarks"
        audit = json.loads(
            (
                benchmark_root
                / "e12-known-19e-suffix-rank-audit-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )
        m04 = json.loads(
            (
                benchmark_root
                / "e12-m04-three-step-search-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )
        tail = json.loads(
            (
                benchmark_root
                / "e16-final-tail-two-step-search-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )
        recheck = json.loads(
            (
                benchmark_root
                / "e16-final-tail-threshold-recheck-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(audit["known_total_e_move"], 19)
        self.assertEqual(len(audit["steps"]), 7)
        self.assertFalse(
            any(
                retained
                for step in audit["steps"]
                for level in step["levels"].values()
                for strategy in ("target_retained", "diverse_retained")
                for retained in level[strategy].values()
            )
        )
        self.assertEqual(m04["exact_first_steps_completed"], 128)
        self.assertEqual(m04["exact_first_steps_timed_out"], 0)
        self.assertEqual(m04["exact_target_candidates_tested"], 19)
        self.assertIsNone(m04["found_total_e_move"])
        self.assertEqual([row["target"] for row in tail["targets"]], [
            "B_plus",
            "B_minus",
        ])
        self.assertTrue(
            all(row["exact_first_steps_completed"] == 128 for row in tail["targets"])
        )
        self.assertIsNone(tail["found_total_e_move"])
        self.assertEqual(recheck["residual_threshold"], 1e-7)
        self.assertTrue(
            all(row["exact_target_candidates_tested"] == 0 for row in recheck["targets"])
        )

    def test_m7_two_step_obligation_scan_is_schema_valid_and_unchecked(self):
        repository_root = Path(__file__).resolve().parents[2]
        artifact = json.loads(
            (
                repository_root
                / "benchmarks"
                / "m7-two-step-obligation-scan-sage-10.7.json"
            ).read_text(encoding="utf-8")
        )
        schema = json.loads(
            (
                repository_root
                / "schemas"
                / "two-step-obligation-scan-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(artifact)

        self.assertEqual(artifact["mode"], "proof_candidate_unchecked")
        self.assertEqual(artifact["forward"]["frontier_states"], 104)
        self.assertEqual(artifact["suffix"]["precursor_candidates"], 4173)
        self.assertEqual(
            artifact["suffix"]["terminal_parameterizations_tested"],
            711795,
        )
        self.assertEqual(artifact["suffix"]["successful_branches"], 0)


class ExactPrefixSearchTests(unittest.TestCase):
    def test_detemple_e12_prefix_rebuilds_with_complete_closure(self):
        node, prefix = exact_prefix("c_M1_2_Ay")

        self.assertEqual(node.score, 12)
        self.assertEqual(prefix[-1]["id"], "c_M1_2_Ay")
        self.assertGreater(len(node.state.points), 2)
        self.assertEqual(len(node.state.lines), 4)
        self.assertEqual(len(node.state.circles), 9)


if __name__ == "__main__":
    unittest.main()
