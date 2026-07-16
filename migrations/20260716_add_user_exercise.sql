-- GYMFIT 사용자별 직접 입력 운동 마이그레이션
-- 대상: MariaDB 11.4.12 / gymfit
-- 이 파일은 아직 마이그레이션을 적용하지 않은 신규 DB용 전체 적용 SQL입니다.
-- user_exercise 또는 workout_plan 변경이 일부라도 적용된 DB에는 다시 실행하지 마십시오.
-- 부분 적용된 DB는 20260716_verify_user_exercise.sql로 현재 상태만 확인하십시오.
-- 주의: MariaDB DDL은 암시적으로 COMMIT될 수 있으므로 START TRANSACTION으로
-- 전체 변경의 원자적 롤백을 보장할 수 없습니다. 아래 문장을 순서대로 실행하고
-- 각 단계가 성공했는지 SHOW CREATE TABLE로 확인한 뒤 다음 단계로 진행하십시오.

-- 적용 전 확인
SELECT VERSION();
SELECT COUNT(*) AS existing_plan_count FROM workout_plan;
SELECT COUNT(*) AS invalid_existing_plan_count
FROM workout_plan
WHERE exercise_id IS NULL;
SHOW CREATE TABLE users;
SHOW CREATE TABLE exercise;
SHOW CREATE TABLE workout_plan;
SHOW INDEX FROM workout_plan;

CREATE TABLE user_exercise (
    user_exercise_id BIGINT(20) NOT NULL AUTO_INCREMENT,
    user_id BIGINT(20) NOT NULL,
    exercise_name VARCHAR(100) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_exercise_id),
    UNIQUE KEY uq_user_exercise_user_name (user_id, exercise_name),
    KEY ix_user_exercise_user_id (user_id),
    CONSTRAINT fk_user_exercise_user
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE workout_plan
    MODIFY exercise_id BIGINT(20) NULL;

ALTER TABLE workout_plan
    ADD COLUMN user_exercise_id BIGINT(20) NULL AFTER exercise_id;

ALTER TABLE workout_plan
    ADD KEY ix_workout_plan_user_exercise_id (user_exercise_id);

ALTER TABLE workout_plan
    ADD CONSTRAINT fk_workout_plan_user_exercise
        FOREIGN KEY (user_exercise_id)
        REFERENCES user_exercise (user_exercise_id)
        ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE workout_plan
    ADD CONSTRAINT uq_workout_plan_user_custom_date
        UNIQUE (user_id, user_exercise_id, plan_date);

-- 적용 후 정합성 확인
SHOW CREATE TABLE user_exercise;
SHOW CREATE TABLE workout_plan;
SHOW INDEX FROM user_exercise;
SHOW INDEX FROM workout_plan;
SELECT COUNT(*) AS preserved_plan_count FROM workout_plan;
SELECT COUNT(*) AS invalid_plan_reference_count
FROM workout_plan
WHERE (exercise_id IS NULL AND user_exercise_id IS NULL)
   OR (exercise_id IS NOT NULL AND user_exercise_id IS NOT NULL);
SELECT COUNT(*) AS orphan_custom_plan_count
FROM workout_plan AS wp
LEFT JOIN user_exercise AS ue
    ON ue.user_exercise_id = wp.user_exercise_id
WHERE wp.user_exercise_id IS NOT NULL
  AND ue.user_exercise_id IS NULL;

-- 중간 실패 시 수동 복구 절차
-- 1. SHOW CREATE TABLE user_exercise와 SHOW CREATE TABLE workout_plan을 실행합니다.
-- 2. 실패한 문장까지 실제 반영된 컬럼, 인덱스, 제약을 확인합니다.
-- 3. 아직 서비스 코드를 배포하지 않았다면 롤백 SQL을 아래에서 위가 아닌
--    기재 순서대로 실행하여 반영된 객체만 제거합니다.
-- 4. DROP 대상이 없다는 오류가 나면 해당 단계는 건너뛰고 다음 문장을 실행합니다.
-- 5. 기존 workout_plan 행 수와 exercise_id NULL 행 수가 적용 전 값과 같은지 확인합니다.
