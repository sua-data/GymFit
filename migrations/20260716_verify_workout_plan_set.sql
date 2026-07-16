-- GYMFIT 세트별 운동 계획 마이그레이션 확인 전용
-- 이 파일은 조회만 수행하며 DB를 변경하지 않습니다.

SELECT COUNT(*) AS workout_plan_set_table_exists
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'workout_plan_set';

SELECT COUNT(*) AS workout_plan_set_fk_exists
FROM information_schema.referential_constraints
WHERE constraint_schema = DATABASE()
  AND table_name = 'workout_plan_set'
  AND constraint_name = 'fk_workout_plan_set_plan';

SELECT COUNT(*) AS plan_order_unique_index_column_count
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'workout_plan_set'
  AND index_name = 'uq_workout_plan_set_plan_order';

SELECT COUNT(*) AS existing_plan_count
FROM workout_plan;

SELECT COUNT(*) AS existing_plan_set_count
FROM workout_plan_set;

SELECT
    wp.workout_plan_id,
    wp.set_count AS summary_set_count,
    COUNT(wps.workout_plan_set_id) AS detail_set_count
FROM workout_plan AS wp
LEFT JOIN workout_plan_set AS wps
    ON wps.workout_plan_id = wp.workout_plan_id
GROUP BY wp.workout_plan_id, wp.set_count
ORDER BY wp.workout_plan_id;

SELECT COUNT(*) AS orphan_set_count
FROM workout_plan_set AS wps
LEFT JOIN workout_plan AS wp
    ON wp.workout_plan_id = wps.workout_plan_id
WHERE wp.workout_plan_id IS NULL;

SELECT COUNT(*) AS duplicate_set_order_group_count
FROM (
    SELECT workout_plan_id, set_order
    FROM workout_plan_set
    GROUP BY workout_plan_id, set_order
    HAVING COUNT(*) > 1
) AS duplicates;

SELECT COUNT(*) AS empty_set_value_count
FROM workout_plan_set
WHERE repetition_count IS NULL
  AND duration_seconds IS NULL;

SELECT COUNT(*) AS negative_value_count
FROM workout_plan_set
WHERE repetition_count < 0
   OR duration_seconds < 0
   OR weight_kg < 0;
