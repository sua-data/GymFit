import unittest

from backend.services.routine_recommendation_service import (
    ExerciseHistory,
    adjust_exercise,
    calculate_completion_rate,
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


if __name__ == "__main__":
    unittest.main()

