-- Existing calories values and calories_per_minute are preserved.
-- Legacy schema requires NOT NULL; records that could not be estimated are restored to 0.
UPDATE workout_record SET calories = 0 WHERE calories IS NULL;

ALTER TABLE workout_record
  DROP COLUMN training_volume_kg,
  DROP COLUMN weight_kg,
  DROP COLUMN calorie_calculation_status,
  DROP COLUMN user_weight_used_kg,
  DROP COLUMN met_used,
  DROP COLUMN intensity_is_default,
  DROP COLUMN exercise_intensity,
  MODIFY COLUMN calories INT NOT NULL DEFAULT 0 COMMENT '소모 칼로리';

ALTER TABLE exercise
  DROP COLUMN met_source_code,
  DROP COLUMN met_source,
  DROP COLUMN met_high,
  DROP COLUMN met_moderate,
  DROP COLUMN met_low;
