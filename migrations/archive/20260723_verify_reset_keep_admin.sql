-- GYMFIT 테스트 데이터 초기화 결과 검증
-- 이 파일은 조회만 수행한다.

SELECT COUNT(*) AS admin_user_count
FROM users
WHERE account_type = 'ADMIN';

SELECT COUNT(*) AS member_user_count
FROM users
WHERE account_type = 'MEMBER';

SELECT COUNT(*) AS trainer_user_count
FROM users
WHERE account_type = 'TRAINER';

SELECT COUNT(*) AS member_profile_count
FROM member_profile;

SELECT COUNT(*) AS trainer_profile_count
FROM trainer_profile;

SELECT COUNT(*) AS trainer_certification_count
FROM trainer_certification;

SELECT COUNT(*) AS trainer_member_count
FROM trainer_member;

SELECT COUNT(*) AS user_gym_count
FROM user_gym;

SELECT COUNT(*) AS gym_machine_count
FROM gym_machine;

SELECT COUNT(*) AS workout_plan_count
FROM workout_plan;

SELECT COUNT(*) AS workout_record_count
FROM workout_record;

SELECT COUNT(*) AS gym_count
FROM gym;

-- 기본 운동 데이터가 유지되었는지 확인한다.
SELECT COUNT(*) AS exercise_count
FROM exercise;

SELECT
    user_id,
    email,
    account_type,
    login_provider,
    is_active,
    created_at
FROM users
WHERE account_type = 'ADMIN'
ORDER BY user_id;

-- 결과가 0행이어야 한다.
SELECT
    user_id,
    email,
    account_type,
    is_active
FROM users
WHERE account_type <> 'ADMIN'
   OR account_type IS NULL
ORDER BY user_id;

-- 요청된 핵심 테이블 외의 사용자 기반 데이터도 0인지 확인한다.
SELECT
    (SELECT COUNT(*) FROM member_goal) AS member_goal_count,
    (SELECT COUNT(*) FROM trainer_specialty) AS trainer_specialty_count,
    (SELECT COUNT(*) FROM user_agreement) AS user_agreement_count,
    (SELECT COUNT(*) FROM user_exercise) AS user_exercise_count,
    (SELECT COUNT(*) FROM email_verification) AS email_verification_count,
    (SELECT COUNT(*) FROM notification) AS notification_count,
    (SELECT COUNT(*) FROM pt_assignment) AS pt_assignment_count,
    (SELECT COUNT(*) FROM pt_feedback) AS pt_feedback_count,
    (SELECT COUNT(*) FROM pt_schedule) AS pt_schedule_count,
    (SELECT COUNT(*) FROM workout_plan_set) AS workout_plan_set_count,
    (SELECT COUNT(*) FROM workout_record_item) AS workout_record_item_count,
    (SELECT COUNT(*) FROM workout_record_media) AS workout_record_media_count;

