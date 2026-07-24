ALTER TABLE workout_record
  DROP FOREIGN KEY fk_workout_record_plan,
  DROP INDEX uq_workout_record_plan,
  DROP COLUMN workout_plan_id;
