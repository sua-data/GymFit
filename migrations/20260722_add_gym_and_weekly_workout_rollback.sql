-- user_gym과 gym의 데이터가 모두 삭제된다. 백업과 데이터 손실 여부를 확인한 후 실행한다.
DROP TABLE IF EXISTS user_gym;
DROP TABLE IF EXISTS gym;
ALTER TABLE member_profile DROP CONSTRAINT chk_member_profile_weekly_workout_days;
ALTER TABLE member_profile DROP COLUMN weekly_workout_days;
