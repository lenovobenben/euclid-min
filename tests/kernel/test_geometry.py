from __future__ import annotations

import unittest

from sage.all import AA

from euclid_min.exact import InexactInputError, sqrt_nonnegative
from euclid_min.geometry import (
    Circle,
    CoincidentPointsError,
    InvalidLineError,
    Line,
    NonPositiveRadiusError,
    Point,
)
from euclid_min.intersections import (
    IntersectionKind,
    intersect,
    intersect_circle_circle,
    intersect_line_circle,
    intersect_line_line,
)
from euclid_min.state import GeometryState, PointNotInStateError
from euclid_min.target import (
    TargetName,
    adjacent_targets,
    reached_targets,
    reached_targets_by_object_pair,
)


class GeometryObjectTests(unittest.TestCase):
    def test_point_and_line_use_exact_equality(self):
        point = Point(AA(1) / 3, sqrt_nonnegative(2))
        self.assertEqual(point, Point(AA(1) / 3, AA(2).sqrt()))
        nearby_rational = AA(3333333333333333) / 10**16
        self.assertNotEqual(point, Point(nearby_rational, AA(2).sqrt()))

        with self.assertRaises(InexactInputError):
            Point(0.3333333333333333, 0)

        first = Line(2, 4, 6)
        second = Line(-1, -2, -3)
        self.assertEqual(first, second)
        self.assertEqual((first.a, first.b, first.c), (AA(1), AA(2), AA(3)))

    def test_invalid_objects_are_rejected(self):
        with self.assertRaises(InvalidLineError):
            Line(0, 0, 1)
        with self.assertRaises(NonPositiveRadiusError):
            Circle(Point(0, 0), 0)
        with self.assertRaises(CoincidentPointsError):
            Line.through(Point(0, 0), Point(0, 0))
        with self.assertRaises(CoincidentPointsError):
            Circle.through(Point(0, 0), Point(0, 0))

    def test_exact_incidence(self):
        origin = Point(0, 0)
        point = Point(1, 1)
        line = Line.through(origin, point)
        circle = Circle.through(origin, point)
        self.assertTrue(line.contains(Point(2, 2)))
        self.assertFalse(line.contains(Point(2, 2 + AA(1) / 10**20)))
        self.assertTrue(circle.contains(point))
        self.assertFalse(circle.contains(Point(1, 1 + AA(1) / 10**20)))


class LineLineIntersectionTests(unittest.TestCase):
    def test_unique_intersection(self):
        horizontal = Line(0, 1, 0)
        vertical = Line(1, 0, 0)
        result = intersect_line_line(horizontal, vertical)
        self.assertEqual(result.kind, IntersectionKind.ONE_POINT)
        self.assertEqual(result.points, (Point(0, 0),))

        general = intersect_line_line(Line(1, 1, -3), Line(1, -1, -1))
        self.assertEqual(general.points, (Point(2, 1),))

    def test_parallel_and_coincident(self):
        first = Line(0, 1, 0)
        parallel = Line(0, 1, -1)
        same = Line(0, -2, 0)
        self.assertEqual(
            intersect_line_line(first, parallel).kind,
            IntersectionKind.PARALLEL,
        )
        self.assertEqual(
            intersect_line_line(first, same).kind,
            IntersectionKind.COINCIDENT,
        )


class LineCircleIntersectionTests(unittest.TestCase):
    def setUp(self):
        self.unit = Circle(Point(0, 0), 1)

    def test_disjoint_tangent_and_two_points(self):
        disjoint = intersect_line_circle(Line(0, 1, -2), self.unit)
        tangent = intersect_line_circle(Line(0, 1, -1), self.unit)
        secant = intersect_line_circle(Line(1, 0, 0), self.unit)

        self.assertEqual(disjoint.kind, IntersectionKind.DISJOINT)
        self.assertEqual(disjoint.points, ())
        self.assertEqual(tangent.kind, IntersectionKind.TANGENT)
        self.assertEqual(tangent.points, (Point(0, 1),))
        self.assertEqual(secant.kind, IntersectionKind.TWO_POINTS)
        self.assertEqual(secant.points, (Point(0, -1), Point(0, 1)))

    def test_dispatch_is_symmetric(self):
        line = Line(0, 1, 0)
        self.assertEqual(intersect(line, self.unit), intersect(self.unit, line))


class CircleCircleIntersectionTests(unittest.TestCase):
    def test_all_relations(self):
        unit = Circle(Point(0, 0), 1)

        coincident = Circle(Point(0, 0), 1)
        contained = Circle(Point(0, 0), 4)
        external_disjoint = Circle(Point(3, 0), 1)
        external_tangent = Circle(Point(2, 0), 1)
        internal_tangent = Circle(Point(1, 0), 4)
        intersecting = Circle(Point(1, 0), 1)

        self.assertEqual(
            intersect_circle_circle(unit, coincident).kind,
            IntersectionKind.COINCIDENT,
        )
        self.assertEqual(
            intersect_circle_circle(unit, contained).kind,
            IntersectionKind.CONTAINED,
        )
        self.assertEqual(
            intersect_circle_circle(unit, external_disjoint).kind,
            IntersectionKind.DISJOINT,
        )

        external_result = intersect_circle_circle(unit, external_tangent)
        self.assertEqual(external_result.kind, IntersectionKind.TANGENT_EXTERNAL)
        self.assertEqual(external_result.points, (Point(1, 0),))

        internal_result = intersect_circle_circle(unit, internal_tangent)
        self.assertEqual(internal_result.kind, IntersectionKind.TANGENT_INTERNAL)
        self.assertEqual(internal_result.points, (Point(-1, 0),))

        two_result = intersect_circle_circle(unit, intersecting)
        root_three_over_two = AA(3).sqrt() / 2
        self.assertEqual(two_result.kind, IntersectionKind.TWO_POINTS)
        self.assertEqual(
            two_result.points,
            (Point(AA(1) / 2, -root_three_over_two), Point(AA(1) / 2, root_three_over_two)),
        )
        self.assertEqual(two_result, intersect_circle_circle(intersecting, unit))


class GeometryStateTests(unittest.TestCase):
    def test_fixed_initial_state_and_automatic_closure(self):
        state = GeometryState.fixed_initial()
        origin = Point(0, 0)
        start = Point(1, 0)

        self.assertEqual(state.points, (origin, start))
        self.assertEqual(len(state.circles), 1)

        line_result = state.draw_line(origin, start)
        self.assertTrue(line_result.new_object)
        self.assertEqual(line_result.new_points, (Point(-1, 0),))
        self.assertEqual(len(state.points), 3)

        duplicate = state.draw_line(origin, start)
        self.assertFalse(duplicate.new_object)
        self.assertEqual(duplicate.new_points, ())
        self.assertEqual(duplicate.intersections, ())

        circle_result = state.draw_circle(start, origin)
        self.assertTrue(circle_result.new_object)
        self.assertEqual(len(circle_result.new_points), 3)
        self.assertEqual(len(state.points), 6)

    def test_draw_requires_existing_points(self):
        state = GeometryState.fixed_initial()
        with self.assertRaises(PointNotInStateError):
            state.draw_line(Point(0, 0), Point(2, 0))


class TargetTests(unittest.TestCase):
    def test_targets_are_exact_points_on_unit_circle(self):
        targets = adjacent_targets()
        unit = Circle(Point(0, 0), 1)
        self.assertTrue(unit.contains(targets[TargetName.B_PLUS]))
        self.assertTrue(unit.contains(targets[TargetName.B_MINUS]))
        self.assertEqual(
            reached_targets(targets.values()),
            (TargetName.B_PLUS, TargetName.B_MINUS),
        )

    def test_nearby_float_point_is_not_target(self):
        target = adjacent_targets()[TargetName.B_PLUS]
        approximate = Point(
            AA(932472229404) / 10**12,
            AA(361241666187) / 10**12,
        )
        self.assertNotEqual(approximate, target)
        self.assertEqual(reached_targets((approximate,)), ())

    def test_targets_can_be_detected_without_materializing_intersections(self):
        targets = adjacent_targets()
        unit = Circle(Point(0, 0), 1)
        vertical_chord = Line(1, 0, -targets[TargetName.B_PLUS].x)
        self.assertEqual(
            reached_targets_by_object_pair(unit, vertical_chord),
            (TargetName.B_PLUS, TargetName.B_MINUS),
        )


if __name__ == "__main__":
    unittest.main()
