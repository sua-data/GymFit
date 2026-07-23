-- GYMFIT test data reset script.
-- Preserves ADMIN users, all exercise rows, and every schema object.
-- This file must be reviewed and run manually.
-- If an error occurs, stop immediately and run ROLLBACK manually.
-- Uploaded image and video files on disk are not removed by this script.

START TRANSACTION;

-- Count preserved administrator accounts.
SET @gymfit_admin_count := (
    SELECT COUNT(*)
    FROM users
    WHERE account_type = 'ADMIN'
);

-- Confirm the preflight result before continuing.
SELECT
    @gymfit_admin_count AS admin_count_before_reset,
    CASE
        WHEN @gymfit_admin_count > 0 THEN 'READY'
        ELSE 'STOP_AND_ROLLBACK'
    END AS reset_preflight_status;

-- Delete PT feedback rows.
DELETE FROM pt_feedback
WHERE @gymfit_admin_count > 0;

-- Delete notification rows.
DELETE FROM notification
WHERE @gymfit_admin_count > 0;

-- Delete workout media rows.
DELETE FROM workout_record_media
WHERE @gymfit_admin_count > 0;

-- Delete workout item rows.
DELETE FROM workout_record_item
WHERE @gymfit_admin_count > 0;

-- Delete PT assignment rows.
DELETE FROM pt_assignment
WHERE @gymfit_admin_count > 0;

-- Delete workout record rows.
DELETE FROM workout_record
WHERE @gymfit_admin_count > 0;

-- Delete PT schedule rows.
DELETE FROM pt_schedule
WHERE @gymfit_admin_count > 0;

-- Delete workout plan set rows.
DELETE FROM workout_plan_set
WHERE @gymfit_admin_count > 0;

-- Delete workout plan rows.
DELETE FROM workout_plan
WHERE @gymfit_admin_count > 0;

-- Delete trainer-member relationship rows.
DELETE FROM trainer_member
WHERE @gymfit_admin_count > 0;

-- Delete gym machine rows.
DELETE FROM gym_machine
WHERE @gymfit_admin_count > 0;

-- Delete user-gym relationship rows.
DELETE FROM user_gym
WHERE @gymfit_admin_count > 0;

-- Delete member goal rows.
DELETE FROM member_goal
WHERE @gymfit_admin_count > 0;

-- Delete member profile rows.
DELETE FROM member_profile
WHERE @gymfit_admin_count > 0;

-- Delete trainer certification rows.
DELETE FROM trainer_certification
WHERE @gymfit_admin_count > 0;

-- Delete trainer specialty rows.
DELETE FROM trainer_specialty
WHERE @gymfit_admin_count > 0;

-- Delete trainer profile rows.
DELETE FROM trainer_profile
WHERE @gymfit_admin_count > 0;

-- Delete user agreement rows.
DELETE FROM user_agreement
WHERE @gymfit_admin_count > 0;

-- Delete user-created exercise rows.
DELETE FROM user_exercise
WHERE @gymfit_admin_count > 0;

-- Delete email verification rows.
DELETE FROM email_verification
WHERE @gymfit_admin_count > 0;

-- Delete test gym rows.
DELETE FROM gym
WHERE @gymfit_admin_count > 0;

-- Delete non-administrator users only.
DELETE FROM users
WHERE @gymfit_admin_count > 0
  AND account_type <> 'ADMIN';

COMMIT;
