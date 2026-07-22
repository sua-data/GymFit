-- MariaDB DDL은 자동 커밋될 수 있습니다. 실행 전 백업하고 문장별 성공 여부를 기록하십시오.
-- 이 파일은 신규 적용용입니다. 이미 생성된 환경에서 전체 파일을 다시 실행하지 마십시오.
SELECT VERSION();
SHOW CREATE TABLE trainer_member;
SHOW CREATE TABLE exercise;
SHOW CREATE TABLE user_exercise;
SHOW CREATE TABLE workout_record;

CREATE TABLE pt_assignment (
  assignment_id BIGINT NOT NULL AUTO_INCREMENT,
  trainer_member_id BIGINT NOT NULL,
  trainer_id BIGINT NOT NULL,
  member_id BIGINT NOT NULL,
  exercise_id BIGINT NULL,
  user_exercise_id BIGINT NULL,
  title VARCHAR(100) NOT NULL,
  description TEXT NULL,
  assigned_date DATE NOT NULL,
  due_date DATE NULL,
  target_sets INT NULL,
  target_reps INT NULL,
  target_minutes INT NULL,
  status ENUM('ASSIGNED','IN_PROGRESS','COMPLETED','CANCELLED') NOT NULL DEFAULT 'ASSIGNED',
  completed_at DATETIME NULL,
  workout_record_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (assignment_id),
  KEY ix_pt_assignment_trainer_status_assigned (trainer_id, status, assigned_date),
  KEY ix_pt_assignment_member_status_due (member_id, status, due_date),
  KEY ix_pt_assignment_trainer_member (trainer_member_id),
  KEY ix_pt_assignment_exercise_id (exercise_id),
  KEY ix_pt_assignment_user_exercise_id (user_exercise_id),
  KEY ix_pt_assignment_workout_record_id (workout_record_id),
  CONSTRAINT fk_pt_assignment_trainer_member FOREIGN KEY (trainer_member_id) REFERENCES trainer_member (trainer_member_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_assignment_trainer FOREIGN KEY (trainer_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_assignment_member FOREIGN KEY (member_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_assignment_exercise FOREIGN KEY (exercise_id) REFERENCES exercise (exercise_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_assignment_user_exercise FOREIGN KEY (user_exercise_id) REFERENCES user_exercise (user_exercise_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_assignment_workout_record FOREIGN KEY (workout_record_id) REFERENCES workout_record (workout_record_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SHOW CREATE TABLE pt_assignment;

ALTER TABLE pt_assignment
MODIFY due_date DATE NULL;

ALTER TABLE pt_assignment
MODIFY updated_at DATETIME NOT NULL
DEFAULT CURRENT_TIMESTAMP
ON UPDATE CURRENT_TIMESTAMP;

SELECT COUNT(*) AS invalid_exercise_reference_count FROM pt_assignment WHERE (exercise_id IS NULL AND user_exercise_id IS NULL) OR (exercise_id IS NOT NULL AND user_exercise_id IS NOT NULL);
SELECT COUNT(*) AS invalid_target_count FROM pt_assignment WHERE COALESCE(target_sets,0) <= 0 AND COALESCE(target_reps,0) <= 0 AND COALESCE(target_minutes,0) <= 0;
SELECT COUNT(*) AS invalid_date_count FROM pt_assignment WHERE due_date IS NOT NULL AND due_date < assigned_date;
SELECT status, COUNT(*) AS status_count FROM pt_assignment GROUP BY status;
SELECT COUNT(*) AS orphan_relationship_count FROM pt_assignment a LEFT JOIN trainer_member tm ON tm.trainer_member_id=a.trainer_member_id WHERE tm.trainer_member_id IS NULL;
