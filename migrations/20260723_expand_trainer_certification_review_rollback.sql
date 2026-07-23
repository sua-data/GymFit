ALTER TABLE trainer_certification
    DROP INDEX ix_trainer_certification_user_active,
    DROP COLUMN is_active,
    DROP COLUMN evidence_original_name,
    DROP COLUMN evidence_storage_path,
    DROP COLUMN certification_number;

ALTER TABLE trainer_profile
    DROP FOREIGN KEY fk_trainer_profile_reviewed_by,
    DROP COLUMN reviewed_at,
    DROP COLUMN reviewed_by;
