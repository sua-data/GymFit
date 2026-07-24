-- Enables transactional/idempotent routine completion records (MariaDB 11.4).
ALTER TABLE workout_record
  ADD COLUMN workout_plan_id BIGINT NULL AFTER pt_schedule_id,
  ADD CONSTRAINT fk_workout_record_plan
    FOREIGN KEY (workout_plan_id) REFERENCES workout_plan(workout_plan_id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  ADD UNIQUE KEY uq_workout_record_plan (workout_plan_id);

-- Verify: no row should be returned.
SELECT workout_plan_id, COUNT(*) AS record_count
FROM workout_record
WHERE workout_plan_id IS NOT NULL
GROUP BY workout_plan_id
HAVING COUNT(*) > 1;
