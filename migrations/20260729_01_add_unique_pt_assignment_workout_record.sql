-- Run 20260729_00_check_pt_assignment_workout_record_duplicates.sql first.
-- MariaDB permits multiple NULL values in a UNIQUE index, so assignments
-- without a linked workout record are unaffected.
ALTER TABLE pt_assignment
  ADD UNIQUE KEY uq_pt_assignment_workout_record (workout_record_id);

-- Verification: no row should be returned.
SELECT workout_record_id, COUNT(*) AS assignment_count
FROM pt_assignment
WHERE workout_record_id IS NOT NULL
GROUP BY workout_record_id
HAVING COUNT(*) > 1;
