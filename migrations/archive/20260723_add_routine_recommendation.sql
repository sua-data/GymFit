-- GYMFIT rule-based routine recommendation
START TRANSACTION;

CREATE TABLE `routine_recommendation` (
  `recommendation_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `recommendation_date` date NOT NULL,
  `goal` varchar(50) NOT NULL,
  `level` varchar(30) NOT NULL,
  `days_per_week` int(11) NOT NULL,
  `workout_minutes` int(11) NOT NULL,
  `source_type` varchar(30) NOT NULL DEFAULT 'RULE_BASED',
  `status` varchar(20) NOT NULL DEFAULT 'RECOMMENDED',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`recommendation_id`),
  KEY `ix_routine_recommendation_user_id` (`user_id`),
  KEY `ix_routine_recommendation_date` (`recommendation_date`),
  CONSTRAINT `fk_routine_recommendation_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ck_routine_recommendation_source`
    CHECK (`source_type` IN ('RULE_BASED')),
  CONSTRAINT `ck_routine_recommendation_status`
    CHECK (`status` IN ('RECOMMENDED', 'APPLIED', 'REPLACED')),
  CONSTRAINT `ck_routine_recommendation_days`
    CHECK (`days_per_week` BETWEEN 1 AND 7),
  CONSTRAINT `ck_routine_recommendation_minutes`
    CHECK (`workout_minutes` BETWEEN 10 AND 240)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `routine_recommendation_item` (
  `recommendation_item_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `recommendation_id` bigint(20) NOT NULL,
  `exercise_id` bigint(20) DEFAULT NULL,
  `user_exercise_id` bigint(20) DEFAULT NULL,
  `workout_date` date NOT NULL,
  `sequence_no` int(11) NOT NULL,
  `recommended_sets` int(11) NOT NULL,
  `recommended_reps` int(11) NOT NULL,
  `difficulty` varchar(30) NOT NULL,
  `coaching_supported` tinyint(1) NOT NULL DEFAULT 0,
  `adjustment_type` varchar(30) NOT NULL,
  `recommendation_reason` text NOT NULL,
  `previous_posture_score` int(11) DEFAULT NULL,
  `previous_completion_rate` decimal(7,4) DEFAULT NULL,
  PRIMARY KEY (`recommendation_item_id`),
  UNIQUE KEY `uq_routine_recommendation_item_sequence` (`recommendation_id`, `sequence_no`),
  KEY `ix_routine_recommendation_item_date` (`workout_date`),
  KEY `ix_routine_recommendation_item_exercise` (`exercise_id`),
  KEY `ix_routine_recommendation_item_user_exercise` (`user_exercise_id`),
  CONSTRAINT `fk_routine_item_recommendation`
    FOREIGN KEY (`recommendation_id`) REFERENCES `routine_recommendation` (`recommendation_id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_routine_item_exercise`
    FOREIGN KEY (`exercise_id`) REFERENCES `exercise` (`exercise_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_routine_item_user_exercise`
    FOREIGN KEY (`user_exercise_id`) REFERENCES `user_exercise` (`user_exercise_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `ck_routine_item_adjustment`
    CHECK (`adjustment_type` IN (
      'BASE', 'MAINTAIN', 'PROGRESS', 'POSTURE_CORRECTION',
      'PERFORMANCE_DOWN', 'REPEATED_FEEDBACK'
    ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `workout_plan`
  ADD COLUMN `recommendation_item_id` bigint(20) DEFAULT NULL AFTER `is_completed`,
  ADD COLUMN `plan_source` varchar(20) NOT NULL DEFAULT 'MANUAL' AFTER `recommendation_item_id`,
  ADD UNIQUE KEY `uq_workout_plan_recommendation_item` (`recommendation_item_id`),
  ADD CONSTRAINT `fk_workout_plan_recommendation_item`
    FOREIGN KEY (`recommendation_item_id`)
    REFERENCES `routine_recommendation_item` (`recommendation_item_id`)
    ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `ck_workout_plan_source`
    CHECK (`plan_source` IN ('MANUAL', 'RECOMMENDED', 'TRAINER'));

COMMIT;

