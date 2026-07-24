-- GYMFIT MET-based estimated calories (MariaDB/MySQL).
-- Source: 2024 Adult Compendium of Physical Activities.
-- calories_per_minute is intentionally retained as a deprecated legacy column.

ALTER TABLE exercise
  ADD COLUMN met_low DECIMAL(4,1) NULL AFTER calories_per_minute,
  ADD COLUMN met_moderate DECIMAL(4,1) NULL AFTER met_low,
  ADD COLUMN met_high DECIMAL(4,1) NULL AFTER met_moderate,
  ADD COLUMN met_source VARCHAR(150) NULL AFTER met_high,
  ADD COLUMN met_source_code VARCHAR(100) NULL AFTER met_source;

ALTER TABLE workout_record
  MODIFY COLUMN calories DECIMAL(10,1) NULL DEFAULT NULL COMMENT '예상 소모 칼로리(kcal)',
  ADD COLUMN exercise_intensity ENUM('LOW','MODERATE','HIGH') NULL AFTER calories,
  ADD COLUMN intensity_is_default TINYINT(1) NULL AFTER exercise_intensity,
  ADD COLUMN met_used DECIMAL(4,1) NULL AFTER intensity_is_default,
  ADD COLUMN user_weight_used_kg DECIMAL(5,2) NULL AFTER met_used,
  ADD COLUMN calorie_calculation_status ENUM('CALCULATED','WEIGHT_REQUIRED','INVALID_DURATION') NULL AFTER user_weight_used_kg,
  ADD COLUMN weight_kg DECIMAL(7,2) NULL COMMENT '해당 운동에서 사용한 중량' AFTER calorie_calculation_status,
  ADD COLUMN training_volume_kg DECIMAL(12,2) NULL AFTER weight_kg;

-- General machine/free-weight resistance: multiple exercises, 8-15 reps (02054);
-- vigorous power lifting/body building (02050).
UPDATE exercise SET met_low=3.5, met_moderate=3.5, met_high=6.0,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='02054|02050'
WHERE exercise_code IN (
  'LEG_PRESS','LEG_EXTENSION','LEG_CURL','HIP_THRUST','CALF_RAISE',
  'BENCH_PRESS','INCLINE_BENCH_PRESS','DUMBBELL_PRESS','CHEST_PRESS',
  'CABLE_FLY','PEC_DECK_FLY','LAT_PULLDOWN','SEATED_ROW','BARBELL_ROW',
  'ONE_ARM_DUMBBELL_ROW','SHOULDER_PRESS','LATERAL_RAISE','FRONT_RAISE',
  'REAR_DELT_FLY','FACE_PULL','BARBELL_CURL','DUMBBELL_CURL','HAMMER_CURL',
  'TRICEPS_PUSHDOWN','OVERHEAD_TRICEPS_EXTENSION'
);

-- Squat/deadlift family: closest specific resistance entry (02052) at moderate.
UPDATE exercise SET met_low=3.5, met_moderate=5.0, met_high=6.0,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='02054|02052|02050'
WHERE exercise_code IN ('SQUAT','ROMANIAN_DEADLIFT','DEADLIFT');

-- Body-weight resistance/calisthenics: general (02056), moderate (02022), high (02057).
UPDATE exercise SET met_low=3.0, met_moderate=3.8, met_high=6.5,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='02056|02022|02057'
WHERE exercise_code IN (
  'PUSHUP','LUNGE','BULGARIAN_SPLIT_SQUAT','PULLUP','DIPS',
  'LEG_RAISE','RUSSIAN_TWIST','MOUNTAIN_CLIMBER'
);

-- Static/light abdominal work (02024), body-weight general/high (02056/02057).
UPDATE exercise SET met_low=2.8, met_moderate=3.0, met_high=6.5,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='02024|02056|02057'
WHERE exercise_code IN ('PLANK','CRUNCH');

-- Cardio equipment has no speed/resistance input. Values are intensity-band defaults;
-- source codes remain stored so future speed/watt-specific selection can replace them.
UPDATE exercise SET met_low=3.5, met_moderate=4.8, met_high=9.0,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='17352|17358|12045'
WHERE exercise_code='TREADMILL';
UPDATE exercise SET met_low=4.0, met_moderate=6.0, met_high=9.0,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='01214|01220|01270'
WHERE exercise_code='STATIONARY_BIKE';
UPDATE exercise SET met_low=4.5, met_moderate=9.3, met_high=9.3,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='17133|02065|17134'
WHERE exercise_code='STEPMILL';
UPDATE exercise SET met_low=5.0, met_moderate=5.0, met_high=9.0,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='02048|02049'
WHERE exercise_code='ELLIPTICAL';
UPDATE exercise SET met_low=5.0, met_moderate=5.0, met_high=7.3,
  met_source='2024 Adult Compendium of Physical Activities',
  met_source_code='02071|02070'
WHERE exercise_code='ROWING_MACHINE';

-- Safety checks: both queries must return zero rows / 43 mapped rows.
SELECT exercise_code, exercise_name FROM exercise
WHERE is_active=1 AND (met_low IS NULL OR met_moderate IS NULL OR met_high IS NULL);
SELECT COUNT(*) AS mapped_exercise_count FROM exercise
WHERE met_low IS NOT NULL AND met_moderate IS NOT NULL AND met_high IS NOT NULL;
