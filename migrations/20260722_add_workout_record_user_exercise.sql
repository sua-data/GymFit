-- MariaDB DDL은 자동 커밋될 수 있습니다. SQL은 파일로만 제공하며 자동 실행하지 않습니다.
SHOW CREATE TABLE user_exercise;
SHOW CREATE TABLE workout_record;
ALTER TABLE user_exercise ADD COLUMN IF NOT EXISTS category VARCHAR(30) NULL AFTER exercise_name;
ALTER TABLE workout_record MODIFY exercise_id BIGINT NULL;
ALTER TABLE workout_record ADD COLUMN user_exercise_id BIGINT NULL AFTER exercise_id;
ALTER TABLE workout_record ADD COLUMN record_source VARCHAR(50) NOT NULL DEFAULT 'COACHING' AFTER user_exercise_id;
ALTER TABLE workout_record ADD COLUMN manual_note TEXT NULL AFTER record_source;
ALTER TABLE workout_record MODIFY average_posture_score INT NULL;
ALTER TABLE workout_record MODIFY best_posture_score INT NULL;
ALTER TABLE workout_record ADD KEY ix_workout_record_user_exercise_id (user_exercise_id);
ALTER TABLE workout_record ADD CONSTRAINT fk_workout_record_user_exercise FOREIGN KEY (user_exercise_id) REFERENCES user_exercise (user_exercise_id) ON DELETE SET NULL ON UPDATE CASCADE;
SELECT COUNT(*) invalid_reference_count FROM workout_record WHERE (exercise_id IS NULL AND user_exercise_id IS NULL) OR (exercise_id IS NOT NULL AND user_exercise_id IS NOT NULL);
SELECT COUNT(*) orphan_custom_record_count FROM workout_record wr LEFT JOIN user_exercise ue ON ue.user_exercise_id=wr.user_exercise_id WHERE wr.user_exercise_id IS NOT NULL AND ue.user_exercise_id IS NULL;