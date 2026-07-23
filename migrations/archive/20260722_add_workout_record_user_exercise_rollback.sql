-- 사용자 운동 기록이 존재하면 롤백 시 데이터 손실을 피하기 위해 중단하고 수동 검토하십시오.
SELECT COUNT(*) custom_record_count FROM workout_record WHERE user_exercise_id IS NOT NULL;
-- 위 결과가 0일 때만 아래 문장을 순서대로 실행하십시오.
ALTER TABLE workout_record DROP FOREIGN KEY fk_workout_record_user_exercise;
ALTER TABLE workout_record DROP INDEX ix_workout_record_user_exercise_id;
ALTER TABLE workout_record DROP COLUMN manual_note;
ALTER TABLE workout_record DROP COLUMN record_source;
ALTER TABLE workout_record DROP COLUMN user_exercise_id;
ALTER TABLE workout_record MODIFY exercise_id BIGINT NOT NULL;
ALTER TABLE workout_record MODIFY average_posture_score INT NOT NULL DEFAULT 0;
ALTER TABLE workout_record MODIFY best_posture_score INT NOT NULL DEFAULT 0;
ALTER TABLE user_exercise DROP COLUMN category;
