-- MariaDB 적용용. 실행 전 workout_record를 백업하십시오.
ALTER TABLE workout_record
  ADD COLUMN record_type ENUM('WORKOUT','PT') NOT NULL DEFAULT 'WORKOUT' AFTER user_id,
  ADD COLUMN title VARCHAR(150) NULL AFTER record_type,
  ADD COLUMN workout_date DATE NULL AFTER title,
  ADD COLUMN workout_part VARCHAR(100) NULL AFTER workout_date,
  ADD COLUMN trainer_id BIGINT NULL AFTER workout_part,
  ADD COLUMN pt_schedule_id BIGINT NULL AFTER trainer_id,
  ADD COLUMN location VARCHAR(200) NULL AFTER pt_schedule_id,
  ADD COLUMN memo TEXT NULL AFTER location,
  ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at,
  ADD UNIQUE KEY uq_workout_record_pt_schedule (pt_schedule_id),
  ADD KEY ix_workout_record_workout_date (workout_date),
  ADD KEY ix_workout_record_trainer_id (trainer_id),
  ADD CONSTRAINT fk_workout_record_trainer FOREIGN KEY (trainer_id) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT fk_workout_record_pt_schedule FOREIGN KEY (pt_schedule_id) REFERENCES pt_schedule(schedule_id) ON DELETE RESTRICT ON UPDATE CASCADE;

UPDATE workout_record
SET record_type = 'WORKOUT',
    workout_date = DATE(started_at),
    title = COALESCE(NULLIF(title, ''), '운동 기록')
WHERE workout_date IS NULL OR title IS NULL OR title = '';

CREATE TABLE workout_record_item (
  item_id BIGINT NOT NULL AUTO_INCREMENT,
  record_id BIGINT NOT NULL,
  exercise_id BIGINT NULL,
  user_exercise_id BIGINT NULL,
  exercise_name VARCHAR(100) NOT NULL,
  weight_value DECIMAL(7,2) NULL,
  weight_text VARCHAR(100) NULL,
  repetitions INT NULL,
  completed_sets INT NULL,
  rpe INT NULL,
  workout_minutes INT NULL,
  memo TEXT NULL,
  posture_score INT NULL,
  feedback TEXT NULL,
  display_order INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (item_id),
  UNIQUE KEY uq_workout_record_item_order (record_id, display_order),
  KEY ix_workout_record_item_record (record_id, display_order),
  KEY ix_workout_record_item_exercise (exercise_id),
  KEY ix_workout_record_item_user_exercise (user_exercise_id),
  CONSTRAINT fk_workout_record_item_record FOREIGN KEY (record_id) REFERENCES workout_record(workout_record_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_workout_record_item_exercise FOREIGN KEY (exercise_id) REFERENCES exercise(exercise_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_workout_record_item_user_exercise FOREIGN KEY (user_exercise_id) REFERENCES user_exercise(user_exercise_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT ck_workout_record_item_rpe CHECK (rpe IS NULL OR (rpe BETWEEN 1 AND 10)),
  CONSTRAINT ck_workout_record_item_weight CHECK (weight_value IS NULL OR weight_value >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE workout_record_media (
  media_id BIGINT NOT NULL AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  media_type ENUM('VIDEO','IMAGE') NOT NULL,
  media_url VARCHAR(500) NOT NULL,
  thumbnail_url VARCHAR(500) NULL,
  storage_path VARCHAR(1000) NOT NULL,
  thumbnail_storage_path VARCHAR(1000) NULL,
  duration_seconds INT NULL,
  file_size BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (media_id),
  KEY ix_workout_record_media_item (item_id, created_at),
  CONSTRAINT fk_workout_record_media_item FOREIGN KEY (item_id) REFERENCES workout_record_item(item_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기존 기록을 단일 상세 항목으로 안전하게 백필합니다. 재실행해도 중복 생성되지 않습니다.
INSERT INTO workout_record_item (
  record_id, exercise_id, user_exercise_id, exercise_name, repetitions,
  completed_sets, workout_minutes, posture_score, feedback, display_order
)
SELECT wr.workout_record_id, wr.exercise_id, wr.user_exercise_id,
       COALESCE(e.exercise_name, ue.exercise_name, wr.title, '운동 기록'),
       NULLIF(wr.repetition_count, 0), NULLIF(wr.completed_sets, 0),
       NULLIF(wr.workout_minutes, 0), wr.average_posture_score, wr.feedback, 1
FROM workout_record wr
LEFT JOIN exercise e ON e.exercise_id = wr.exercise_id
LEFT JOIN user_exercise ue ON ue.user_exercise_id = wr.user_exercise_id
WHERE NOT EXISTS (
  SELECT 1 FROM workout_record_item item WHERE item.record_id = wr.workout_record_id
);

SELECT COUNT(*) AS workout_session_count FROM workout_record;
SELECT COUNT(*) AS workout_item_count FROM workout_record_item;
