-- 알림 행은 유지하고 새 이동 메타데이터 컬럼만 제거합니다.
-- 세 컬럼에 저장된 값은 손실되므로 롤백 전 반드시 확인하십시오.

SELECT COUNT(*) AS typed_notification_count
FROM notification
WHERE notification_type IS NOT NULL
   OR target_url IS NOT NULL
   OR reference_id IS NOT NULL;

ALTER TABLE notification
    DROP COLUMN reference_id,
    DROP COLUMN target_url,
    DROP COLUMN notification_type;

SHOW CREATE TABLE notification;
