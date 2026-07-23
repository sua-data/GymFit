ALTER TABLE trainer_profile
    ADD COLUMN reviewed_by BIGINT NULL AFTER rejection_reason,
    ADD COLUMN reviewed_at DATETIME NULL AFTER reviewed_by,
    ADD CONSTRAINT fk_trainer_profile_reviewed_by
        FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE trainer_certification
    ADD COLUMN certification_number VARCHAR(100) NULL AFTER certification_name,
    ADD COLUMN evidence_storage_path VARCHAR(1000) NULL AFTER evidence_image_url,
    ADD COLUMN evidence_original_name VARCHAR(255) NULL AFTER evidence_storage_path,
    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1 AFTER evidence_original_name,
    ADD INDEX ix_trainer_certification_user_active (user_id, is_active);
