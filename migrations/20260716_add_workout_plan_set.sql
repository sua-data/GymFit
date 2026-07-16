-- GYMFIT 세트별 운동 계획 마이그레이션
-- 대상: MariaDB 11.4.12 / gymfit
-- MariaDB DDL은 암시적으로 COMMIT될 수 있으므로 전체 원자적 롤백이 보장되지 않습니다.
-- 이 파일은 DB 클라이언트에서 상태를 확인하며 문장별로 실행하십시오.

-- 적용 전 확인
SELECT VERSION();
SHOW CREATE TABLE workout_plan;
SELECT COUNT(*) AS existing_plan_count FROM workout_plan;
SELECT
    MIN(set_count) AS minimum_set_count,
    MAX(set_count) AS maximum_set_count
FROM workout_plan;
SELECT COUNT(*) AS invalid_legacy_plan_count
FROM workout_plan
WHERE set_count < 1
   OR set_count > 100
   OR repetition_count < 1;

CREATE TABLE workout_plan_set (
    workout_plan_set_id BIGINT(20) NOT NULL AUTO_INCREMENT,
    workout_plan_id BIGINT(20) NOT NULL,
    set_order INT NOT NULL,
    repetition_count INT NULL,
    duration_seconds INT NULL,
    weight_kg DECIMAL(7,2) NULL,
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (workout_plan_set_id),
    UNIQUE KEY uq_workout_plan_set_plan_order (workout_plan_id, set_order),
    KEY ix_workout_plan_set_workout_plan_id (workout_plan_id),
    CONSTRAINT fk_workout_plan_set_plan
        FOREIGN KEY (workout_plan_id)
        REFERENCES workout_plan (workout_plan_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기존 workout_plan 요약값으로 세트 상세 생성
-- NOT EXISTS 조건 때문에 계획에 세트가 하나라도 있으면 다시 생성하지 않습니다.
INSERT INTO workout_plan_set (
    workout_plan_id,
    set_order,
    repetition_count,
    duration_seconds,
    weight_kg,
    is_completed
)
SELECT
    wp.workout_plan_id,
    numbers.set_order,
    wp.repetition_count,
    NULL,
    NULL,
    wp.is_completed
FROM workout_plan AS wp
JOIN (
    SELECT ones.value + tens.value * 10 + 1 AS set_order
    FROM (
        SELECT 0 AS value UNION ALL SELECT 1 UNION ALL SELECT 2
        UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
        UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
        UNION ALL SELECT 9
    ) AS ones
    CROSS JOIN (
        SELECT 0 AS value UNION ALL SELECT 1 UNION ALL SELECT 2
        UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
        UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
        UNION ALL SELECT 9
    ) AS tens
) AS numbers
    ON numbers.set_order <= wp.set_count
WHERE wp.set_count BETWEEN 1 AND 100
  AND wp.repetition_count >= 1
  AND NOT EXISTS (
      SELECT 1
      FROM workout_plan_set AS existing_set
      WHERE existing_set.workout_plan_id = wp.workout_plan_id
  );

-- 적용 후 정합성 확인
SHOW CREATE TABLE workout_plan_set;
SHOW INDEX FROM workout_plan_set;
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
