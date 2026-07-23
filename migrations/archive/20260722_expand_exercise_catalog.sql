-- MariaDB DDL은 자동 커밋될 수 있습니다. 실제 DB에는 자동 실행되지 않습니다.
SHOW CREATE TABLE exercise;
SELECT exercise_code, exercise_name FROM exercise WHERE exercise_code IN ('SQUAT','PUSHUP','SHOULDER_PRESS');

ALTER TABLE exercise ADD COLUMN IF NOT EXISTS category VARCHAR(30) NULL AFTER exercise_name;

UPDATE exercise SET category='하체' WHERE exercise_code='SQUAT' AND category IS NULL;
UPDATE exercise SET category='가슴' WHERE exercise_code='PUSHUP' AND category IS NULL;
UPDATE exercise SET category='어깨' WHERE exercise_code='SHOULDER_PRESS' AND category IS NULL;

INSERT INTO exercise (exercise_code, exercise_name, category, calories_per_minute, is_active)
SELECT source.exercise_code, source.exercise_name, source.category, source.calories_per_minute, 1
FROM (
  SELECT 'LEG_PRESS' exercise_code, '레그 프레스' exercise_name, '하체' category, 5.00 calories_per_minute UNION ALL
  SELECT 'LEG_EXTENSION','레그 익스텐션','하체',4.00 UNION ALL SELECT 'LEG_CURL','레그 컬','하체',4.00 UNION ALL
  SELECT 'LUNGE','런지','하체',5.00 UNION ALL SELECT 'BULGARIAN_SPLIT_SQUAT','불가리안 스플릿 스쿼트','하체',5.00 UNION ALL
  SELECT 'HIP_THRUST','힙 스러스트','하체',5.00 UNION ALL SELECT 'ROMANIAN_DEADLIFT','루마니안 데드리프트','하체',6.00 UNION ALL SELECT 'CALF_RAISE','카프 레이즈','하체',4.00 UNION ALL
  SELECT 'BENCH_PRESS','벤치 프레스','가슴',5.00 UNION ALL SELECT 'INCLINE_BENCH_PRESS','인클라인 벤치 프레스','가슴',5.00 UNION ALL SELECT 'DUMBBELL_PRESS','덤벨 프레스','가슴',5.00 UNION ALL SELECT 'CHEST_PRESS','체스트 프레스','가슴',5.00 UNION ALL SELECT 'CABLE_FLY','케이블 플라이','가슴',4.00 UNION ALL SELECT 'PEC_DECK_FLY','펙 덱 플라이','가슴',4.00 UNION ALL
  SELECT 'LAT_PULLDOWN','랫 풀다운','등',5.00 UNION ALL SELECT 'SEATED_ROW','시티드 로우','등',5.00 UNION ALL SELECT 'BARBELL_ROW','바벨 로우','등',6.00 UNION ALL SELECT 'ONE_ARM_DUMBBELL_ROW','원암 덤벨 로우','등',5.00 UNION ALL SELECT 'PULLUP','풀업','등',7.00 UNION ALL SELECT 'DEADLIFT','데드리프트','등',7.00 UNION ALL
  SELECT 'LATERAL_RAISE','사이드 레터럴 레이즈','어깨',4.00 UNION ALL SELECT 'FRONT_RAISE','프론트 레이즈','어깨',4.00 UNION ALL SELECT 'REAR_DELT_FLY','리어 델트 플라이','어깨',4.00 UNION ALL SELECT 'FACE_PULL','페이스 풀','어깨',4.00 UNION ALL
  SELECT 'BARBELL_CURL','바벨 컬','팔',4.00 UNION ALL SELECT 'DUMBBELL_CURL','덤벨 컬','팔',4.00 UNION ALL SELECT 'HAMMER_CURL','해머 컬','팔',4.00 UNION ALL SELECT 'TRICEPS_PUSHDOWN','트라이셉스 푸시다운','팔',4.00 UNION ALL SELECT 'OVERHEAD_TRICEPS_EXTENSION','오버헤드 트라이셉스 익스텐션','팔',4.00 UNION ALL SELECT 'DIPS','딥스','팔',6.00 UNION ALL
  SELECT 'PLANK','플랭크','코어',3.00 UNION ALL SELECT 'CRUNCH','크런치','코어',4.00 UNION ALL SELECT 'LEG_RAISE','레그 레이즈','코어',4.00 UNION ALL SELECT 'RUSSIAN_TWIST','러시안 트위스트','코어',5.00 UNION ALL SELECT 'MOUNTAIN_CLIMBER','마운틴 클라이머','코어',8.00 UNION ALL
  SELECT 'TREADMILL','러닝머신','유산소',8.00 UNION ALL SELECT 'STATIONARY_BIKE','실내 자전거','유산소',7.00 UNION ALL SELECT 'STEPMILL','스텝밀','유산소',9.00 UNION ALL SELECT 'ELLIPTICAL','일립티컬','유산소',7.00 UNION ALL SELECT 'ROWING_MACHINE','로잉 머신','유산소',8.00
) source
LEFT JOIN exercise existing ON existing.exercise_code=source.exercise_code
WHERE existing.exercise_id IS NULL;

ALTER TABLE user_exercise
ADD COLUMN IF NOT EXISTS category VARCHAR(30) NULL
AFTER exercise_name;

SELECT category, COUNT(*) exercise_count FROM exercise WHERE is_active=1 GROUP BY category ORDER BY category;
SELECT exercise_code, COUNT(*) duplicate_count FROM exercise GROUP BY exercise_code HAVING COUNT(*)>1;
SHOW COLUMNS FROM user_exercise LIKE 'category';