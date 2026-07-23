ALTER TABLE trainer_profile
    ADD COLUMN rejection_reason VARCHAR(500) NULL AFTER approval_status;

ALTER TABLE trainer_certification
    ADD COLUMN evidence_image_url VARCHAR(500) NULL AFTER acquired_date;
