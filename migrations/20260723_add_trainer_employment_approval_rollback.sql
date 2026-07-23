ALTER TABLE trainer_profile
    DROP INDEX ix_trainer_profile_employment_status,
    DROP FOREIGN KEY fk_trainer_profile_employment_reviewed_by,
    DROP COLUMN employment_rejection_reason,
    DROP COLUMN employment_reviewed_at,
    DROP COLUMN employment_reviewed_by,
    DROP COLUMN employment_original_name,
    DROP COLUMN employment_storage_path,
    DROP COLUMN employment_evidence_url,
    DROP COLUMN employment_status;
