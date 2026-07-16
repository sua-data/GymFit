-- GYMFIT 사용자별 직접 입력 운동 롤백
-- 주의: MariaDB DDL은 암시적으로 COMMIT될 수 있습니다.
-- 아래 사전 확인 결과 custom_plan_count가 0일 때만 롤백하십시오.

SELECT COUNT(*) AS custom_plan_count
FROM workout_plan
WHERE user_exercise_id IS NOT NULL;
SHOW CREATE TABLE workout_plan;
SHOW CREATE TABLE user_exercise;

ALTER TABLE workout_plan
    DROP INDEX uq_workout_plan_user_custom_date;

ALTER TABLE workout_plan
    DROP FOREIGN KEY fk_workout_plan_user_exercise;

ALTER TABLE workout_plan
    DROP INDEX ix_workout_plan_user_exercise_id;

ALTER TABLE workout_plan
    DROP COLUMN user_exercise_id;

ALTER TABLE workout_plan
    MODIFY exercise_id BIGINT(20) NOT NULL;

DROP TABLE user_exercise;

SHOW CREATE TABLE workout_plan;
SHOW INDEX FROM workout_plan;
SELECT COUNT(*) AS null_exercise_plan_count
FROM workout_plan
WHERE exercise_id IS NULL;
