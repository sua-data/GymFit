-- Preflight check before adding uq_pt_assignment_workout_record.
-- The result must be empty before running the apply migration.
SELECT
  workout_record_id,
  COUNT(*) AS assignment_count,
  GROUP_CONCAT(assignment_id ORDER BY assignment_id) AS assignment_ids
FROM pt_assignment
WHERE workout_record_id IS NOT NULL
GROUP BY workout_record_id
HAVING COUNT(*) > 1;

-- Optional detail view for resolving every duplicate group.
SELECT
  pa.assignment_id,
  pa.workout_record_id,
  pa.trainer_id,
  pa.member_id,
  pa.status,
  pa.completed_at
FROM pt_assignment AS pa
INNER JOIN (
  SELECT workout_record_id
  FROM pt_assignment
  WHERE workout_record_id IS NOT NULL
  GROUP BY workout_record_id
  HAVING COUNT(*) > 1
) AS duplicate
  ON duplicate.workout_record_id = pa.workout_record_id
ORDER BY pa.workout_record_id, pa.assignment_id;
