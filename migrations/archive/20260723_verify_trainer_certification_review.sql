SHOW COLUMNS FROM trainer_profile
WHERE Field IN ('approval_status', 'rejection_reason', 'reviewed_by', 'reviewed_at');

SHOW COLUMNS FROM trainer_certification;
SHOW INDEX FROM trainer_certification;

SELECT approval_status, COUNT(*) AS trainer_count
FROM trainer_profile
GROUP BY approval_status;
