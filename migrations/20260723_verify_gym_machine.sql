SHOW CREATE TABLE gym_machine;
SHOW INDEX FROM gym_machine;
SELECT gym_id, is_active, COUNT(*) AS machine_count
FROM gym_machine
GROUP BY gym_id, is_active
ORDER BY gym_id, is_active;
