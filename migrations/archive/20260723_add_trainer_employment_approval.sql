ALTER TABLE trainer_profile
    ADD COLUMN employment_status ENUM('NONE', 'PENDING', 'APPROVED', 'REJECTED')
        NOT NULL DEFAULT 'NONE' AFTER reviewed_at,
    ADD COLUMN employment_evidence_url VARCHAR(500) NULL AFTER employment_status,
    ADD COLUMN employment_storage_path VARCHAR(1000) NULL AFTER employment_evidence_url,
    ADD COLUMN employment_original_name VARCHAR(255) NULL AFTER employment_storage_path,
    ADD COLUMN employment_reviewed_by BIGINT NULL AFTER employment_original_name,
    ADD COLUMN employment_reviewed_at DATETIME NULL AFTER employment_reviewed_by,
    ADD COLUMN employment_rejection_reason VARCHAR(500) NULL AFTER employment_reviewed_at,
    ADD CONSTRAINT fk_trainer_profile_employment_reviewed_by
        FOREIGN KEY (employment_reviewed_by) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    ADD INDEX ix_trainer_profile_employment_status (employment_status);

-- 기존 승인 트레이너의 현재 헬스장 권한은 마이그레이션으로 끊지 않는다.
-- 이후 헬스장을 변경하면 애플리케이션이 소속 상태를 PENDING으로 전환한다.
UPDATE trainer_profile tp
JOIN users u ON u.user_id = tp.user_id
JOIN user_gym ug ON ug.user_id = tp.user_id
SET tp.employment_status = 'APPROVED'
WHERE u.account_type = 'TRAINER'
  AND u.is_active = 1
  AND tp.approval_status = 'APPROVED';
