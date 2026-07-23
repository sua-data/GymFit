-- MariaDB 11.4.12용 신규 trainer_member 전체 적용 SQL입니다.
-- MariaDB DDL은 자동 커밋될 수 있으므로 실행 전 반드시 백업하십시오.
-- 이미 trainer_member 테이블이 존재하면 이 파일 전체를 다시 실행하지 마십시오.

SELECT VERSION() AS mariadb_version;
SHOW TABLES LIKE 'users';
SHOW TABLES LIKE 'trainer_member';
SHOW CREATE TABLE users;

CREATE TABLE trainer_member (
    trainer_member_id BIGINT NOT NULL AUTO_INCREMENT,
    trainer_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    status ENUM('PENDING','ACTIVE','ENDED') NOT NULL DEFAULT 'PENDING',
    started_at DATE NULL,
    ended_at DATE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (trainer_member_id),
    INDEX ix_trainer_member_trainer_status (trainer_id, status),
    INDEX ix_trainer_member_member_status (member_id, status),
    INDEX ix_trainer_member_pair_status (trainer_id, member_id, status),
    CONSTRAINT fk_trainer_member_trainer
        FOREIGN KEY (trainer_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_trainer_member_member
        FOREIGN KEY (member_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SHOW CREATE TABLE trainer_member;

SELECT COUNT(*) AS self_relationship_count
FROM trainer_member
WHERE trainer_id = member_id;

SELECT COUNT(*) AS invalid_role_count
FROM trainer_member tm
JOIN users trainer ON trainer.user_id = tm.trainer_id
JOIN users member ON member.user_id = tm.member_id
WHERE trainer.account_type <> 'TRAINER'
   OR member.account_type <> 'MEMBER';

SELECT trainer_id, member_id, COUNT(*) AS open_relationship_count
FROM trainer_member
WHERE status IN ('PENDING', 'ACTIVE')
GROUP BY trainer_id, member_id
HAVING COUNT(*) > 1;

SELECT member_id, COUNT(*) AS active_trainer_count
FROM trainer_member
WHERE status = 'ACTIVE'
GROUP BY member_id
HAVING COUNT(*) > 1;

SELECT COUNT(*) AS orphan_relationship_count
FROM trainer_member tm
LEFT JOIN users trainer ON trainer.user_id = tm.trainer_id
LEFT JOIN users member ON member.user_id = tm.member_id
WHERE trainer.user_id IS NULL OR member.user_id IS NULL;

-- PENDING/ACTIVE 부분 UNIQUE와 MEMBER별 ACTIVE 1건 제약은 MariaDB의 일반 UNIQUE로
-- ENDED 재요청을 허용하면서 표현하기 어려워 백엔드 트랜잭션과 사용자 행 잠금으로 검증합니다.
