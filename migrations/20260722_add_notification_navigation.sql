-- MariaDB 11.4.12용 notification 이동 정보 필드 추가 SQL입니다.
-- DDL은 자동 커밋될 수 있으므로 실행 전 백업하고 문장별 결과를 확인하십시오.
-- 기존 notification 행은 삭제하거나 변경하지 않습니다.

SHOW TABLES LIKE 'notification';
SHOW CREATE TABLE notification;

ALTER TABLE notification
    ADD COLUMN notification_type VARCHAR(50) NULL AFTER message,
    ADD COLUMN target_url VARCHAR(500) NULL AFTER notification_type,
    ADD COLUMN reference_id BIGINT NULL AFTER target_url;

SHOW COLUMNS FROM notification LIKE 'notification_type';
SHOW COLUMNS FROM notification LIKE 'target_url';
SHOW COLUMNS FROM notification LIKE 'reference_id';

SELECT COUNT(*) AS existing_notification_count FROM notification;
SELECT COUNT(*) AS invalid_target_url_count
FROM notification
WHERE target_url IS NOT NULL AND target_url NOT LIKE '/%';
