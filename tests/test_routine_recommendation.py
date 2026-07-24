import unittest
from datetime import date
from types import SimpleNamespace

from backend.services.routine_recommendation_service import (
    ExerciseHistory,
    adjust_exercise,
    build_weekly_exercise_schedule,
    calculate_completion_rate,
    daily_exercise_count,
    has_consecutive_run,
    recommendation_dates,
    select_training_days,
)


class RoutineAdjustmentTests(unittest.TestCase):
    def test_zero_target_is_safe(self):
        self.assertIsNone(calculate_completion_rate(10, 0))
        self.assertIsNone(calculate_completion_rate(10, None))

    def test_new_user_gets_base_recommendation(self):
        result = adjust_exercise(10, ExerciseHistory(), "스쿼트")
        self.assertEqual((result.reps, result.adjustment_type), (10, "BASE"))

    def test_low_posture_reduces_reps(self):
        result = adjust_exercise(
            10, ExerciseHistory(posture_score=67, completion_rate=1.0), "스쿼트"
        )
        self.assertEqual((result.reps, result.adjustment_type), (8, "POSTURE_CORRECTION"))

    def test_high_score_and_completion_progresses(self):
        result = adjust_exercise(
            10, ExerciseHistory(posture_score=90, completion_rate=1.0), "스쿼트"
        )
        self.assertEqual((result.reps, result.adjustment_type), (12, "PROGRESS"))

    def test_low_completion_blocks_progress(self):
        result = adjust_exercise(
            10, ExerciseHistory(posture_score=95, completion_rate=0.6), "스쿼트"
        )
        self.assertEqual((result.reps, result.adjustment_type), (8, "PERFORMANCE_DOWN"))

    def test_repeated_feedback_takes_priority(self):
        result = adjust_exercise(
            6,
            ExerciseHistory(
                posture_score=90,
                completion_rate=1.0,
                repeated_feedback="무릎이 안쪽으로 모입니다",
            ),
            "스쿼트",
        )
        self.assertEqual((result.reps, result.adjustment_type), (5, "REPEATED_FEEDBACK"))
        self.assertIn("무릎이 안쪽으로 모입니다", result.reason)


class RoutineScheduleTests(unittest.TestCase):
    def test_two_days_are_spread(self):
        self.assertEqual(select_training_days(2), ("MON", "THU"))
        self.assertFalse(has_consecutive_run(select_training_days(2), 2))

    def test_three_days_are_evenly_spread(self):
        self.assertEqual(select_training_days(3), ("MON", "WED", "FRI"))
        self.assertFalse(has_consecutive_run(select_training_days(3), 2))

    def test_four_days_never_have_four_consecutive_days(self):
        days = select_training_days(4)
        self.assertEqual(days, ("MON", "TUE", "THU", "SAT"))
        self.assertFalse(has_consecutive_run(days, 4))

    def test_all_four_day_variants_avoid_four_consecutive_days(self):
        variants = [select_training_days(4, variant=index) for index in range(6)]
        self.assertTrue(
            all(not has_consecutive_run(days, 4) for days in variants)
        )
        self.assertNotEqual(variants[0], variants[1])

    def test_five_days_include_recovery_days(self):
        days = select_training_days(5)
        self.assertEqual(len(days), 5)
        self.assertLess(len(days), 7)
        self.assertFalse(has_consecutive_run(days, 4))

    def test_sunday_and_monday_are_consecutive(self):
        self.assertTrue(has_consecutive_run(("SUN", "MON"), 2))

    def test_preferred_days_are_preserved(self):
        preferred = ["TUE", "WED", "FRI", "SUN"]
        self.assertEqual(select_training_days(4, preferred), tuple(preferred))
        dates = recommendation_dates(date(2026, 7, 20), 4, preferred)
        self.assertEqual(
            {item.weekday() for item in dates},
            {1, 2, 4, 6},
        )


class DailyExerciseCountTests(unittest.TestCase):
    def test_beginner_defaults_to_four(self):
        self.assertEqual(daily_exercise_count("BEGINNER", 40), 4)

    def test_intermediate_defaults_to_five(self):
        self.assertEqual(daily_exercise_count("INTERMEDIATE", 40), 5)

    def test_thirty_minutes_is_three_to_four(self):
        self.assertIn(daily_exercise_count("ADVANCED", 30), (3, 4))

    def test_low_completion_does_not_increase_volume(self):
        self.assertEqual(daily_exercise_count("INTERMEDIATE", 40, 0.5), 4)

    def test_daily_count_never_exceeds_six(self):
        self.assertLessEqual(daily_exercise_count("ADVANCED", 120), 6)


class ExerciseDistributionTests(unittest.TestCase):
    @staticmethod
    def exercises():
        categories = ["하체", "가슴", "등", "복근", "유산소", "어깨", "팔"]
        return [
            SimpleNamespace(
                exercise_id=index,
                exercise_code=f"EX_{index}",
                exercise_name=f"운동 {index}",
                category=categories[index % len(categories)],
            )
            for index in range(1, 30)
        ]

    def test_exercises_do_not_repeat_on_consecutive_training_days(self):
        schedule = build_weekly_exercise_schedule(
            self.exercises(), 4, 5, [], "ENDURANCE"
        )
        self.assertTrue(all(len(day) == 5 for day in schedule))
        for previous, current in zip(schedule, schedule[1:]):
            self.assertTrue(
                {item.exercise_id for item in previous}.isdisjoint(
                    item.exercise_id for item in current
                )
            )

    def test_same_exercise_is_recommended_at_most_twice(self):
        exercises = [
            SimpleNamespace(
                exercise_id=index,
                exercise_code=f"EX_{index}",
                exercise_name=f"운동 {index}",
                category=("하체", "가슴", "등", "복근", "유산소")[index % 5],
            )
            for index in range(1, 24)
        ]
        schedule = build_weekly_exercise_schedule(
            exercises, 5, 4, [], "WEIGHT_LOSS"
        )
        counts = {}
        for exercise in (item for day in schedule for item in day):
            counts[exercise.exercise_id] = counts.get(exercise.exercise_id, 0) + 1
        self.assertLessEqual(max(counts.values()), 2)

    def test_same_variant_is_reproducible(self):
        first = build_weekly_exercise_schedule(
            self.exercises(), 4, 5, ["EX_1", "EX_2", "EX_3"], "ENDURANCE", 2
        )
        second = build_weekly_exercise_schedule(
            self.exercises(), 4, 5, ["EX_1", "EX_2", "EX_3"], "ENDURANCE", 2
        )
        self.assertEqual(
            [[item.exercise_id for item in day] for day in first],
            [[item.exercise_id for item in day] for day in second],
        )

    def test_different_variants_change_safe_composition(self):
        first = build_weekly_exercise_schedule(
            self.exercises(), 4, 5, ["EX_1", "EX_2", "EX_3"], "ENDURANCE", 0
        )
        second = build_weekly_exercise_schedule(
            self.exercises(), 4, 5, ["EX_1", "EX_2", "EX_3"], "ENDURANCE", 1
        )
        self.assertNotEqual(
            [[item.exercise_id for item in day] for day in first],
            [[item.exercise_id for item in day] for day in second],
        )


if __name__ == "__main__":
    unittest.main()
