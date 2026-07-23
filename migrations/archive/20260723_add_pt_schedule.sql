-- MariaDB 신규 적용용. 실행 전 백업하고 문장별 성공 여부를 확인하십시오.
SELECT VERSION();
SHOW CREATE TABLE trainer_member;

CREATE TABLE pt_schedule (
  schedule_id BIGINT NOT NULL AUTO_INCREMENT,
  trainer_member_id BIGINT NOT NULL,
  trainer_id BIGINT NOT NULL,
  member_id BIGINT NOT NULL,
  start_at DATETIME NOT NULL,
  end_at DATETIME NOT NULL,
  location VARCHAR(200) NULL,
  memo TEXT NULL,
  status ENUM('SCHEDULED','CANCELLED','COMPLETED') NOT NULL DEFAULT 'SCHEDULED',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (schedule_id),
  KEY ix_pt_schedule_trainer_status_start (trainer_id, status, start_at),
  KEY ix_pt_schedule_member_status_start (member_id, status, start_at),
  KEY ix_pt_schedule_relationship_start (trainer_member_id, start_at),
  CONSTRAINT ck_pt_schedule_time_range CHECK (end_at > start_at),
  CONSTRAINT fk_pt_schedule_trainer_member FOREIGN KEY (trainer_member_id) REFERENCES trainer_member (trainer_member_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_schedule_trainer FOREIGN KEY (trainer_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pt_schedule_member FOREIGN KEY (member_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SHOW CREATE TABLE pt_schedule;
SELECT status, COUNT(*) AS status_count FROM pt_schedule GROUP BY status;
