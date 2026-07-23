-- MariaDB 11.4.12. DDL은 자동 커밋될 수 있으므로 문장별 결과를 확인한다.
-- 이 파일은 신규 구조 전체 적용용이며 이미 일부 적용된 DB에 통째로 재실행하지 않는다.

ALTER TABLE member_profile
    ADD COLUMN weekly_workout_days TINYINT UNSIGNED NULL
        COMMENT '주간 목표 운동 일수'
        AFTER exercise_level,
    ADD CONSTRAINT chk_member_profile_weekly_workout_days
        CHECK (weekly_workout_days IS NULL OR weekly_workout_days BETWEEN 1 AND 7);

CREATE TABLE gym (
    gym_id BIGINT NOT NULL AUTO_INCREMENT,
    provider VARCHAR(20) NOT NULL,
    external_place_id VARCHAR(100) NOT NULL,
    gym_name VARCHAR(150) NOT NULL,
    road_address VARCHAR(255) NOT NULL,
    address VARCHAR(255) NULL,
    latitude DECIMAL(10,7) NULL,
    longitude DECIMAL(10,7) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (gym_id),
    CONSTRAINT uq_gym_provider_external_place UNIQUE (provider, external_place_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_gym (
    user_gym_id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    gym_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_gym_id),
    CONSTRAINT uq_user_gym_user UNIQUE (user_id),
    INDEX ix_user_gym_gym_id (gym_id),
    CONSTRAINT fk_user_gym_user FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_user_gym_gym FOREIGN KEY (gym_id) REFERENCES gym (gym_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT COUNT(*) AS invalid_weekly_workout_days
FROM member_profile
WHERE weekly_workout_days IS NOT NULL
  AND weekly_workout_days NOT BETWEEN 1 AND 7;

SELECT COUNT(*) AS orphan_user_gym_count
FROM user_gym ug
LEFT JOIN users u ON u.user_id = ug.user_id
LEFT JOIN gym g ON g.gym_id = ug.gym_id
WHERE u.user_id IS NULL OR g.gym_id IS NULL;

SHOW COLUMNS FROM member_profile LIKE 'weekly_workout_days';

SHOW TABLES LIKE 'gym';
ALTER TABLE gym
    MODIFY COLUMN updated_at DATETIME NOT NULL
    DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

SHOW TABLES LIKE 'user_gym';
ALTER TABLE gym
    MODIFY COLUMN updated_at DATETIME NOT NULL
    DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE user_gym
    MODIFY COLUMN updated_at DATETIME NOT NULL
    DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP;

SHOW CREATE TABLE gym;
SHOW CREATE TABLE user_gym;
SHOW CREATE TABLE member_profile;

SELECT COUNT(*) AS invalid_weekly_workout_days
FROM member_profile
WHERE weekly_workout_days IS NOT NULL
  AND weekly_workout_days NOT BETWEEN 1 AND 7;

SELECT COUNT(*) AS orphan_user_gym_count
FROM user_gym ug
LEFT JOIN users u ON u.user_id = ug.user_id
LEFT JOIN gym g ON g.gym_id = ug.gym_id
WHERE u.user_id IS NULL OR g.gym_id IS NULL;
