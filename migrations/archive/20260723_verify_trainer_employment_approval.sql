SHOW COLUMNS FROM trainer_profile
WHERE Field LIKE 'employment_%';

SHOW INDEX FROM trainer_profile
WHERE Key_name = 'ix_trainer_profile_employment_status';

SELECT employment_status, COUNT(*) AS trainer_count
FROM trainer_profile
GROUP BY employment_status;
