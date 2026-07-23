-- 경고: 상세 운동과 업로드 미디어 메타데이터 및 PT 세션 연결 정보가 삭제됩니다.
-- 실제 업로드 파일은 별도로 백업/정리해야 합니다.
DROP TABLE IF EXISTS workout_record_media;
DROP TABLE IF EXISTS workout_record_item;
ALTER TABLE workout_record
  DROP FOREIGN KEY fk_workout_record_pt_schedule,
  DROP FOREIGN KEY fk_workout_record_trainer,
  DROP INDEX uq_workout_record_pt_schedule,
  DROP INDEX ix_workout_record_workout_date,
  DROP INDEX ix_workout_record_trainer_id,
  DROP COLUMN updated_at,
  DROP COLUMN memo,
  DROP COLUMN location,
  DROP COLUMN pt_schedule_id,
  DROP COLUMN trainer_id,
  DROP COLUMN workout_part,
  DROP COLUMN workout_date,
  DROP COLUMN title,
  DROP COLUMN record_type;
