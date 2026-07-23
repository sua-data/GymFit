-- GYMFIT 사용자 운동 마이그레이션 부분 적용 상태 확인 전용
-- 이 파일은 조회만 수행하며 DB 구조나 데이터를 변경하지 않습니다.

SELECT
    COUNT(*) AS user_exercise_table_exists
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'user_exercise';

SELECT
    COUNT(*) AS workout_plan_user_exercise_id_exists
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'workout_plan'
  AND column_name = 'user_exercise_id';

SELECT
    COUNT(*) AS user_exercise_fk_exists
FROM information_schema.referential_constraints
WHERE constraint_schema = DATABASE()
  AND table_name = 'workout_plan'
  AND constraint_name = 'fk_workout_plan_user_exercise';

SELECT
    COUNT(*) AS custom_plan_unique_index_exists
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'workout_plan'
  AND index_name = 'uq_workout_plan_user_custom_date';

SELECT
    COUNT(*) AS existing_plan_count
FROM workout_plan;

SELECT
    COUNT(*) AS both_references_null_count
FROM workout_plan
WHERE exercise_id IS NULL
  AND user_exercise_id IS NULL;

SELECT
    COUNT(*) AS both_references_present_count
FROM workout_plan
WHERE exercise_id IS NOT NULL
  AND user_exercise_id IS NOT NULL;

SELECT
    COUNT(*) AS orphan_user_exercise_reference_count
FROM workout_plan AS wp
LEFT JOIN user_exercise AS ue
    ON ue.user_exercise_id = wp.user_exercise_id
WHERE wp.user_exercise_id IS NOT NULL
  AND ue.user_exercise_id IS NULL;
