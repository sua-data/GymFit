-- MariaDB DDL은 자동 커밋될 수 있습니다. 이 파일은 신규 적용용이며 자동 실행되지 않습니다.
SELECT VERSION();
SHOW CREATE TABLE pt_assignment;
SHOW CREATE TABLE workout_record;
SHOW CREATE TABLE users;

CREATE TABLE pt_feedback (
  feedback_id BIGINT NOT NULL AUTO_INCREMENT,
  assignment_id BIGINT NOT NULL,
  workout_record_id BIGINT NOT NULL,
  trainer_id BIGINT NOT NULL,
  member_id BIGINT NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (feedback_id),
  UNIQUE KEY uq_pt_feedback_assignment (assignment_id),
  KEY ix_pt_feedback_workout_record (workout_record_id),
  KEY ix_pt_feedback_trainer (trainer_id),
  KEY ix_pt_feedback_member_updated (member_id, updated_at),
  CONSTRAINT fk_pt_feedback_assignment FOREIGN KEY (assignment_id) REFERENCES pt_assignment (assignment_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_feedback_workout_record FOREIGN KEY (workout_record_id) REFERENCES workout_record (workout_record_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_feedback_trainer FOREIGN KEY (trainer_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_feedback_member FOREIGN KEY (member_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SHOW CREATE TABLE pt_feedback;
SELECT COUNT(*) AS orphan_assignment_count FROM pt_feedback f LEFT JOIN pt_assignment a ON a.assignment_id=f.assignment_id WHERE a.assignment_id IS NULL;
SELECT COUNT(*) AS orphan_record_count FROM pt_feedback f LEFT JOIN workout_record r ON r.workout_record_id=f.workout_record_id WHERE r.workout_record_id IS NULL;
SELECT COUNT(*) AS ownership_mismatch_count FROM pt_feedback f JOIN pt_assignment a ON a.assignment_id=f.assignment_id WHERE f.trainer_id<>a.trainer_id OR f.member_id<>a.member_id OR f.workout_record_id<>a.workout_record_id;
SELECT assignment_id, COUNT(*) AS duplicate_count FROM pt_feedback GROUP BY assignment_id HAVING COUNT(*)>1;
