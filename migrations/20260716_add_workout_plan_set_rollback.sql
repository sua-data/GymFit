-- GYMFIT 세트별 운동 계획 롤백
-- 경고: 이 테이블에 저장된 세트별 무게, 횟수, 시간 데이터가 모두 삭제됩니다.
-- 기존 workout_plan 테이블과 set_count, repetition_count, estimated_minutes는 보존됩니다.
-- MariaDB DDL은 암시적으로 COMMIT될 수 있습니다.

SELECT COUNT(*) AS workout_plan_set_count
FROM workout_plan_set;

SELECT COUNT(DISTINCT workout_plan_id) AS plan_with_detail_set_count
FROM workout_plan_set;

SHOW CREATE TABLE workout_plan_set;

DROP TABLE workout_plan_set;

SHOW CREATE TABLE workout_plan;
SELECT COUNT(*) AS preserved_plan_count
FROM workout_plan;
