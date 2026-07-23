/* GYMFIT schema baseline: 2026-07-23
 * Schema only. No application data is included.
 * Run only against a new, empty database.
 */

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;

--
-- Table structure for table `email_verification`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `email_verification` (
  `email_verification_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '이메일 인증 고유 번호',
  `email` varchar(255) NOT NULL COMMENT '인증 대상 이메일',
  `verification_code_hash` varchar(255) NOT NULL COMMENT '암호화된 이메일 인증번호',
  `purpose` enum('SIGNUP','PASSWORD_RESET') NOT NULL DEFAULT 'SIGNUP' COMMENT '인증 목적',
  `is_verified` tinyint(1) NOT NULL DEFAULT 0 COMMENT '인증 완료 여부',
  `attempt_count` int(11) NOT NULL DEFAULT 0 COMMENT '인증번호 확인 시도 횟수',
  `expires_at` datetime NOT NULL COMMENT '인증번호 만료 일시',
  `verified_at` datetime DEFAULT NULL COMMENT '인증 완료 일시',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '인증번호 생성 일시',
  PRIMARY KEY (`email_verification_id`),
  KEY `idx_email_verification_email` (`email`),
  KEY `idx_email_verification_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='이메일 인증번호 관리';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exercise`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `exercise` (
  `exercise_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '운동 종목 고유 번호',
  `exercise_code` varchar(50) NOT NULL COMMENT '운동 종목 코드',
  `exercise_name` varchar(100) NOT NULL COMMENT '운동 종목명',
  `category` varchar(30) DEFAULT NULL,
  `calories_per_minute` decimal(5,2) NOT NULL DEFAULT 0.00 COMMENT '분당 예상 소모 칼로리',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '사용 여부',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '등록 일시',
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '수정 일시',
  PRIMARY KEY (`exercise_id`),
  UNIQUE KEY `ix_exercise_exercise_code` (`exercise_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gym`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `gym` (
  `gym_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `provider` varchar(20) NOT NULL,
  `external_place_id` varchar(100) NOT NULL,
  `gym_name` varchar(150) NOT NULL,
  `road_address` varchar(255) NOT NULL,
  `address` varchar(255) DEFAULT NULL,
  `phone` varchar(50) DEFAULT NULL,
  `place_url` varchar(500) DEFAULT NULL,
  `category_name` varchar(255) DEFAULT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`gym_id`),
  UNIQUE KEY `uq_gym_provider_external_place` (`provider`,`external_place_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gym_machine`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `gym_machine` (
  `machine_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `gym_id` bigint(20) NOT NULL,
  `machine_name` varchar(120) NOT NULL,
  `body_part` varchar(30) NOT NULL,
  `brand` varchar(100) DEFAULT NULL,
  `model_name` varchar(120) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `usage_guide` text DEFAULT NULL,
  `caution` text DEFAULT NULL,
  `image_url` varchar(500) DEFAULT NULL,
  `image_storage_path` varchar(1000) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_by` bigint(20) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`machine_id`),
  KEY `fk_gym_machine_created_by` (`created_by`),
  KEY `ix_gym_machine_gym_active` (`gym_id`,`is_active`),
  KEY `ix_gym_machine_gym_name` (`gym_id`,`machine_name`),
  CONSTRAINT `fk_gym_machine_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_gym_machine_gym` FOREIGN KEY (`gym_id`) REFERENCES `gym` (`gym_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `member_goal`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `member_goal` (
  `member_goal_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '운동 목표 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT 'users 테이블의 회원 번호',
  `goal_code` varchar(50) NOT NULL COMMENT '운동 목표 코드',
  `goal_name` varchar(100) NOT NULL COMMENT '화면에 표시할 운동 목표명',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '운동 목표 등록 일시',
  PRIMARY KEY (`member_goal_id`),
  UNIQUE KEY `uq_member_goal` (`user_id`,`goal_code`),
  CONSTRAINT `fk_member_goal_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='일반 회원 운동 목표';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `member_profile`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `member_profile` (
  `member_profile_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '일반 회원 프로필 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT 'users 테이블의 회원 번호',
  `height_cm` decimal(5,2) DEFAULT NULL COMMENT '키(cm)',
  `weight_kg` decimal(5,2) DEFAULT NULL COMMENT '몸무게(kg)',
  `exercise_level` enum('BEGINNER','INTERMEDIATE','ADVANCED') DEFAULT NULL COMMENT '운동 수준: 초급, 중급, 고급',
  `weekly_workout_days` tinyint(3) unsigned DEFAULT NULL COMMENT '주간 목표 운동 일수',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '프로필 생성 일시',
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '프로필 수정 일시',
  PRIMARY KEY (`member_profile_id`),
  UNIQUE KEY `uq_member_profile_user` (`user_id`),
  CONSTRAINT `fk_member_profile_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_member_profile_weekly_workout_days` CHECK (`weekly_workout_days` is null or `weekly_workout_days` between 1 and 7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='일반 회원 상세 프로필';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notification`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `notification` (
  `notification_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '알림 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT '회원 번호',
  `title` varchar(150) NOT NULL COMMENT '알림 제목',
  `message` text NOT NULL COMMENT '알림 내용',
  `notification_type` varchar(50) DEFAULT NULL,
  `target_url` varchar(500) DEFAULT NULL,
  `reference_id` bigint(20) DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT 0 COMMENT '읽음 여부',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '알림 생성 일시',
  PRIMARY KEY (`notification_id`),
  KEY `ix_notification_user_id` (`user_id`),
  KEY `ix_notification_created_at` (`created_at`),
  KEY `ix_notification_is_read` (`is_read`),
  CONSTRAINT `notification_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pt_assignment`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pt_assignment` (
  `assignment_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `trainer_member_id` bigint(20) NOT NULL,
  `trainer_id` bigint(20) NOT NULL,
  `member_id` bigint(20) NOT NULL,
  `exercise_id` bigint(20) DEFAULT NULL,
  `user_exercise_id` bigint(20) DEFAULT NULL,
  `title` varchar(150) NOT NULL,
  `description` text DEFAULT NULL,
  `assigned_date` date NOT NULL,
  `due_date` date DEFAULT NULL,
  `target_sets` int(11) DEFAULT NULL,
  `target_reps` int(11) DEFAULT NULL,
  `target_minutes` int(11) DEFAULT NULL,
  `status` enum('ASSIGNED','IN_PROGRESS','COMPLETED','CANCELLED') NOT NULL DEFAULT 'ASSIGNED',
  `completed_at` datetime DEFAULT NULL,
  `workout_record_id` bigint(20) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`assignment_id`),
  KEY `exercise_id` (`exercise_id`),
  KEY `user_exercise_id` (`user_exercise_id`),
  KEY `workout_record_id` (`workout_record_id`),
  KEY `ix_pt_assignment_trainer_status_due` (`trainer_id`,`status`,`due_date`),
  KEY `ix_pt_assignment_trainer_member` (`trainer_member_id`),
  KEY `ix_pt_assignment_member_status_due` (`member_id`,`status`,`due_date`),
  CONSTRAINT `pt_assignment_ibfk_1` FOREIGN KEY (`trainer_member_id`) REFERENCES `trainer_member` (`trainer_member_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_assignment_ibfk_2` FOREIGN KEY (`trainer_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_assignment_ibfk_3` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_assignment_ibfk_4` FOREIGN KEY (`exercise_id`) REFERENCES `exercise` (`exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_assignment_ibfk_5` FOREIGN KEY (`user_exercise_id`) REFERENCES `user_exercise` (`user_exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_assignment_ibfk_6` FOREIGN KEY (`workout_record_id`) REFERENCES `workout_record` (`workout_record_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pt_feedback`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pt_feedback` (
  `feedback_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint(20) NOT NULL,
  `workout_record_id` bigint(20) NOT NULL,
  `trainer_id` bigint(20) NOT NULL,
  `member_id` bigint(20) NOT NULL,
  `content` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`feedback_id`),
  UNIQUE KEY `uq_pt_feedback_assignment` (`assignment_id`),
  KEY `workout_record_id` (`workout_record_id`),
  KEY `trainer_id` (`trainer_id`),
  KEY `member_id` (`member_id`),
  CONSTRAINT `pt_feedback_ibfk_1` FOREIGN KEY (`assignment_id`) REFERENCES `pt_assignment` (`assignment_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_feedback_ibfk_2` FOREIGN KEY (`workout_record_id`) REFERENCES `workout_record` (`workout_record_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_feedback_ibfk_3` FOREIGN KEY (`trainer_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_feedback_ibfk_4` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pt_schedule`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pt_schedule` (
  `schedule_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `trainer_member_id` bigint(20) NOT NULL,
  `trainer_id` bigint(20) NOT NULL,
  `member_id` bigint(20) NOT NULL,
  `start_at` datetime NOT NULL,
  `end_at` datetime NOT NULL,
  `location` varchar(200) DEFAULT NULL,
  `memo` text DEFAULT NULL,
  `status` enum('SCHEDULED','CANCELLED','COMPLETED') NOT NULL DEFAULT 'SCHEDULED',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`schedule_id`),
  KEY `ix_pt_schedule_relationship_start` (`trainer_member_id`,`start_at`),
  KEY `ix_pt_schedule_trainer_status_start` (`trainer_id`,`status`,`start_at`),
  KEY `ix_pt_schedule_member_status_start` (`member_id`,`status`,`start_at`),
  CONSTRAINT `pt_schedule_ibfk_1` FOREIGN KEY (`trainer_member_id`) REFERENCES `trainer_member` (`trainer_member_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_schedule_ibfk_2` FOREIGN KEY (`trainer_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `pt_schedule_ibfk_3` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE,
  CONSTRAINT `ck_pt_schedule_time_range` CHECK (`end_at` > `start_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `routine_recommendation`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
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
  CONSTRAINT `fk_routine_recommendation_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ck_routine_recommendation_source` CHECK (`source_type` = 'RULE_BASED'),
  CONSTRAINT `ck_routine_recommendation_status` CHECK (`status` in ('RECOMMENDED','APPLIED','REPLACED')),
  CONSTRAINT `ck_routine_recommendation_days` CHECK (`days_per_week` between 1 and 7),
  CONSTRAINT `ck_routine_recommendation_minutes` CHECK (`workout_minutes` between 10 and 240)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `routine_recommendation_item`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
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
  UNIQUE KEY `uq_routine_recommendation_item_sequence` (`recommendation_id`,`sequence_no`),
  KEY `ix_routine_recommendation_item_date` (`workout_date`),
  KEY `ix_routine_recommendation_item_exercise` (`exercise_id`),
  KEY `ix_routine_recommendation_item_user_exercise` (`user_exercise_id`),
  CONSTRAINT `fk_routine_item_exercise` FOREIGN KEY (`exercise_id`) REFERENCES `exercise` (`exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_routine_item_recommendation` FOREIGN KEY (`recommendation_id`) REFERENCES `routine_recommendation` (`recommendation_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_routine_item_user_exercise` FOREIGN KEY (`user_exercise_id`) REFERENCES `user_exercise` (`user_exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `ck_routine_item_adjustment` CHECK (`adjustment_type` in ('BASE','MAINTAIN','PROGRESS','POSTURE_CORRECTION','PERFORMANCE_DOWN','REPEATED_FEEDBACK'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trainer_certification`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `trainer_certification` (
  `trainer_certification_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '자격증 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT 'users 테이블의 트레이너 회원 번호',
  `certification_name` varchar(150) NOT NULL COMMENT '자격증 이름',
  `certification_number` varchar(100) DEFAULT NULL,
  `issuer` varchar(150) DEFAULT NULL COMMENT '자격증 발급 기관',
  `acquired_date` date DEFAULT NULL COMMENT '자격증 취득일',
  `evidence_image_url` varchar(500) DEFAULT NULL,
  `evidence_storage_path` varchar(1000) DEFAULT NULL,
  `evidence_original_name` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '자격증 등록 일시',
  PRIMARY KEY (`trainer_certification_id`),
  UNIQUE KEY `uq_trainer_certification` (`user_id`,`certification_name`),
  KEY `ix_trainer_certification_user_active` (`user_id`,`is_active`),
  CONSTRAINT `fk_trainer_certification_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='트레이너 자격증';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trainer_member`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `trainer_member` (
  `trainer_member_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `trainer_id` bigint(20) NOT NULL,
  `member_id` bigint(20) NOT NULL,
  `status` enum('PENDING','ACTIVE','ENDED') NOT NULL DEFAULT 'PENDING',
  `started_at` date DEFAULT NULL,
  `ended_at` date DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`trainer_member_id`),
  KEY `ix_trainer_member_trainer_status` (`trainer_id`,`status`),
  KEY `ix_trainer_member_member_status` (`member_id`,`status`),
  KEY `ix_trainer_member_pair_status` (`trainer_id`,`member_id`,`status`),
  CONSTRAINT `fk_trainer_member_member` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_trainer_member_trainer` FOREIGN KEY (`trainer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trainer_profile`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `trainer_profile` (
  `trainer_profile_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '트레이너 프로필 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT 'users 테이블의 회원 번호',
  `gym_name` varchar(150) DEFAULT NULL COMMENT '소속 또는 근무 헬스장 이름',
  `career_years` int(11) DEFAULT NULL COMMENT '트레이너 경력 연수',
  `introduction` varchar(300) DEFAULT NULL COMMENT '트레이너 자기소개',
  `approval_status` enum('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING' COMMENT '트레이너 승인 상태',
  `rejection_reason` varchar(500) DEFAULT NULL,
  `reviewed_by` bigint(20) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `employment_status` enum('NONE','PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'NONE',
  `employment_evidence_url` varchar(500) DEFAULT NULL,
  `employment_storage_path` varchar(1000) DEFAULT NULL,
  `employment_original_name` varchar(255) DEFAULT NULL,
  `employment_reviewed_by` bigint(20) DEFAULT NULL,
  `employment_reviewed_at` datetime DEFAULT NULL,
  `employment_rejection_reason` varchar(500) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '프로필 생성 일시',
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '프로필 수정 일시',
  PRIMARY KEY (`trainer_profile_id`),
  UNIQUE KEY `uq_trainer_profile_user` (`user_id`),
  KEY `fk_trainer_profile_reviewed_by` (`reviewed_by`),
  KEY `fk_trainer_profile_employment_reviewed_by` (`employment_reviewed_by`),
  KEY `ix_trainer_profile_employment_status` (`employment_status`),
  CONSTRAINT `fk_trainer_profile_employment_reviewed_by` FOREIGN KEY (`employment_reviewed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_trainer_profile_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_trainer_profile_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='트레이너 상세 프로필';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trainer_specialty`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `trainer_specialty` (
  `trainer_specialty_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '전문 분야 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT 'users 테이블의 트레이너 회원 번호',
  `specialty_code` varchar(50) NOT NULL COMMENT '전문 분야 코드',
  `specialty_name` varchar(100) NOT NULL COMMENT '화면에 표시할 전문 분야명',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '전문 분야 등록 일시',
  PRIMARY KEY (`trainer_specialty_id`),
  UNIQUE KEY `uq_trainer_specialty` (`user_id`,`specialty_code`),
  CONSTRAINT `fk_trainer_specialty_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='트레이너 전문 분야';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_agreement`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_agreement` (
  `user_id` bigint(20) NOT NULL,
  `terms_agreed` tinyint(1) NOT NULL DEFAULT 0,
  `privacy_agreed` tinyint(1) NOT NULL DEFAULT 0,
  `marketing_agreed` tinyint(1) NOT NULL DEFAULT 0,
  `trainer_policy_agreed` tinyint(1) NOT NULL DEFAULT 0,
  `agreed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`user_id`),
  CONSTRAINT `fk_user_agreement_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_exercise`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_exercise` (
  `user_exercise_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `exercise_name` varchar(100) NOT NULL,
  `category` varchar(30) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`user_exercise_id`),
  UNIQUE KEY `uq_user_exercise_user_name` (`user_id`,`exercise_name`),
  KEY `ix_user_exercise_user_id` (`user_id`),
  CONSTRAINT `fk_user_exercise_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_gym`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_gym` (
  `user_gym_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `gym_id` bigint(20) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`user_gym_id`),
  UNIQUE KEY `uq_user_gym_user` (`user_id`),
  KEY `ix_user_gym_gym_id` (`gym_id`),
  CONSTRAINT `user_gym_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_gym_ibfk_2` FOREIGN KEY (`gym_id`) REFERENCES `gym` (`gym_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '회원 고유 번호',
  `account_type` enum('MEMBER','TRAINER','ADMIN') NOT NULL COMMENT '??? ???',
  `name` varchar(50) NOT NULL COMMENT '회원 이름',
  `email` varchar(255) NOT NULL COMMENT '로그인 및 이메일 인증에 사용하는 이메일',
  `login_provider` enum('LOCAL','GOOGLE') NOT NULL DEFAULT 'LOCAL' COMMENT '로그인 제공자',
  `google_sub` varchar(255) DEFAULT NULL COMMENT 'Google 계정 고유 식별자',
  `password_hash` varchar(255) DEFAULT NULL COMMENT '암호화된 비밀번호, 소셜 로그인 계정은 NULL',
  `gender` enum('MALE','FEMALE','NONE') NOT NULL DEFAULT 'NONE' COMMENT '성별',
  `birth_date` date DEFAULT NULL COMMENT '생년월일',
  `is_email_verified` tinyint(1) NOT NULL DEFAULT 0 COMMENT '이메일 인증 완료 여부',
  `must_change_password` tinyint(1) NOT NULL DEFAULT 0 COMMENT '비밀번호 변경 필요 여부',
  `temporary_password_expires_at` datetime DEFAULT NULL COMMENT '임시 비밀번호 만료 일시',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '계정 활성화 여부',
  `last_login_at` datetime DEFAULT NULL COMMENT '마지막 로그인 일시',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '회원가입 일시',
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '회원 정보 수정 일시',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uq_users_email` (`email`),
  UNIQUE KEY `uq_users_google_sub` (`google_sub`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GYMFIT 회원 공통 정보';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_plan`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_plan` (
  `workout_plan_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '운동 계획 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT '회원 번호',
  `exercise_id` bigint(20) DEFAULT NULL,
  `user_exercise_id` bigint(20) DEFAULT NULL,
  `plan_date` date NOT NULL COMMENT '운동 예정일',
  `set_count` int(11) NOT NULL DEFAULT 1 COMMENT '계획 세트 수',
  `repetition_count` int(11) NOT NULL DEFAULT 0 COMMENT '세트당 반복 횟수',
  `estimated_minutes` int(11) NOT NULL DEFAULT 0 COMMENT '예상 운동 시간',
  `is_completed` tinyint(1) NOT NULL DEFAULT 0 COMMENT '완료 여부',
  `recommendation_item_id` bigint(20) DEFAULT NULL,
  `plan_source` varchar(20) NOT NULL DEFAULT 'MANUAL',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '등록 일시',
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '수정 일시',
  PRIMARY KEY (`workout_plan_id`),
  UNIQUE KEY `uq_workout_plan_user_exercise_date` (`user_id`,`exercise_id`,`plan_date`),
  UNIQUE KEY `uq_workout_plan_user_custom_date` (`user_id`,`user_exercise_id`,`plan_date`),
  UNIQUE KEY `uq_workout_plan_recommendation_item` (`recommendation_item_id`),
  KEY `ix_workout_plan_exercise_id` (`exercise_id`),
  KEY `ix_workout_plan_user_id` (`user_id`),
  KEY `ix_workout_plan_plan_date` (`plan_date`),
  KEY `ix_workout_plan_user_exercise_id` (`user_exercise_id`),
  CONSTRAINT `fk_workout_plan_recommendation_item` FOREIGN KEY (`recommendation_item_id`) REFERENCES `routine_recommendation_item` (`recommendation_item_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_workout_plan_user_exercise` FOREIGN KEY (`user_exercise_id`) REFERENCES `user_exercise` (`user_exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `workout_plan_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `workout_plan_ibfk_2` FOREIGN KEY (`exercise_id`) REFERENCES `exercise` (`exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `ck_workout_plan_source` CHECK (`plan_source` in ('MANUAL','RECOMMENDED','TRAINER'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_plan_set`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_plan_set` (
  `workout_plan_set_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `workout_plan_id` bigint(20) NOT NULL,
  `set_order` int(11) NOT NULL,
  `repetition_count` int(11) DEFAULT NULL,
  `duration_seconds` int(11) DEFAULT NULL,
  `weight_kg` decimal(7,2) DEFAULT NULL,
  `is_completed` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`workout_plan_set_id`),
  UNIQUE KEY `uq_workout_plan_set_plan_order` (`workout_plan_id`,`set_order`),
  KEY `ix_workout_plan_set_workout_plan_id` (`workout_plan_id`),
  CONSTRAINT `fk_workout_plan_set_plan` FOREIGN KEY (`workout_plan_id`) REFERENCES `workout_plan` (`workout_plan_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_record`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_record` (
  `workout_record_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '운동 기록 고유 번호',
  `user_id` bigint(20) NOT NULL COMMENT '회원 번호',
  `record_type` enum('WORKOUT','PT') NOT NULL DEFAULT 'WORKOUT',
  `title` varchar(150) DEFAULT NULL,
  `workout_date` date DEFAULT NULL,
  `workout_part` varchar(100) DEFAULT NULL,
  `trainer_id` bigint(20) DEFAULT NULL,
  `pt_schedule_id` bigint(20) DEFAULT NULL,
  `location` varchar(200) DEFAULT NULL,
  `memo` text DEFAULT NULL,
  `exercise_id` bigint(20) DEFAULT NULL,
  `user_exercise_id` bigint(20) DEFAULT NULL,
  `record_source` varchar(50) NOT NULL DEFAULT 'COACHING',
  `manual_note` text DEFAULT NULL,
  `started_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '운동 시작 일시',
  `completed_at` datetime DEFAULT NULL COMMENT '운동 완료 일시',
  `completed_sets` int(11) NOT NULL DEFAULT 0 COMMENT '완료 세트 수',
  `repetition_count` int(11) NOT NULL DEFAULT 0 COMMENT '전체 반복 횟수',
  `workout_minutes` int(11) NOT NULL DEFAULT 0 COMMENT '운동 시간',
  `calories` int(11) NOT NULL DEFAULT 0 COMMENT '소모 칼로리',
  `average_posture_score` int(11) DEFAULT NULL,
  `best_posture_score` int(11) DEFAULT NULL,
  `feedback_title` varchar(150) DEFAULT NULL COMMENT '자세 피드백 제목',
  `feedback` text DEFAULT NULL COMMENT '자세 피드백 내용',
  `image_url` varchar(500) DEFAULT NULL COMMENT '분석 이미지 URL',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '기록 생성 일시',
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`workout_record_id`),
  UNIQUE KEY `uq_workout_record_pt_schedule` (`pt_schedule_id`),
  KEY `ix_workout_record_started_at` (`started_at`),
  KEY `ix_workout_record_exercise_id` (`exercise_id`),
  KEY `ix_workout_record_user_id` (`user_id`),
  KEY `ix_workout_record_user_exercise_id` (`user_exercise_id`),
  KEY `ix_workout_record_workout_date` (`workout_date`),
  KEY `ix_workout_record_trainer_id` (`trainer_id`),
  CONSTRAINT `fk_workout_record_pt_schedule` FOREIGN KEY (`pt_schedule_id`) REFERENCES `pt_schedule` (`schedule_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_workout_record_trainer` FOREIGN KEY (`trainer_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_workout_record_user_exercise` FOREIGN KEY (`user_exercise_id`) REFERENCES `user_exercise` (`user_exercise_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `workout_record_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `workout_record_ibfk_2` FOREIGN KEY (`exercise_id`) REFERENCES `exercise` (`exercise_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_record_item`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_record_item` (
  `item_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `record_id` bigint(20) NOT NULL,
  `exercise_id` bigint(20) DEFAULT NULL,
  `user_exercise_id` bigint(20) DEFAULT NULL,
  `exercise_name` varchar(100) NOT NULL,
  `weight_value` decimal(7,2) DEFAULT NULL,
  `weight_text` varchar(100) DEFAULT NULL,
  `repetitions` int(11) DEFAULT NULL,
  `completed_sets` int(11) DEFAULT NULL,
  `rpe` int(11) DEFAULT NULL,
  `workout_minutes` int(11) DEFAULT NULL,
  `memo` text DEFAULT NULL,
  `posture_score` int(11) DEFAULT NULL,
  `feedback` text DEFAULT NULL,
  `display_order` int(11) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`item_id`),
  UNIQUE KEY `uq_workout_record_item_order` (`record_id`,`display_order`),
  KEY `ix_workout_record_item_record` (`record_id`,`display_order`),
  KEY `ix_workout_record_item_exercise` (`exercise_id`),
  KEY `ix_workout_record_item_user_exercise` (`user_exercise_id`),
  CONSTRAINT `fk_workout_record_item_exercise` FOREIGN KEY (`exercise_id`) REFERENCES `exercise` (`exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_workout_record_item_record` FOREIGN KEY (`record_id`) REFERENCES `workout_record` (`workout_record_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_workout_record_item_user_exercise` FOREIGN KEY (`user_exercise_id`) REFERENCES `user_exercise` (`user_exercise_id`) ON UPDATE CASCADE,
  CONSTRAINT `ck_workout_record_item_rpe` CHECK (`rpe` is null or `rpe` between 1 and 10),
  CONSTRAINT `ck_workout_record_item_weight` CHECK (`weight_value` is null or `weight_value` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_record_media`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_record_media` (
  `media_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `item_id` bigint(20) NOT NULL,
  `media_type` enum('VIDEO','IMAGE') NOT NULL,
  `media_url` varchar(500) NOT NULL,
  `thumbnail_url` varchar(500) DEFAULT NULL,
  `storage_path` varchar(1000) NOT NULL,
  `thumbnail_storage_path` varchar(1000) DEFAULT NULL,
  `duration_seconds` int(11) DEFAULT NULL,
  `file_size` bigint(20) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`media_id`),
  KEY `ix_workout_record_media_item` (`item_id`,`created_at`),
  CONSTRAINT `fk_workout_record_media_item` FOREIGN KEY (`item_id`) REFERENCES `workout_record_item` (`item_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
