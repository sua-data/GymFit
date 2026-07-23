SET @gymfit_admin_email = 'gymfit.noreply@gmail.com';

START TRANSACTION;

SELECT
  user_id,
  email,
  account_type,
  login_provider,
  is_active
FROM users
WHERE
  email COLLATE utf8mb4_unicode_ci =
  TRIM(@gymfit_admin_email) COLLATE utf8mb4_unicode_ci
FOR UPDATE;

UPDATE users
SET account_type = 'ADMIN'
WHERE
  email COLLATE utf8mb4_unicode_ci =
  TRIM(@gymfit_admin_email) COLLATE utf8mb4_unicode_ci
  AND is_active = 1;

SELECT ROW_COUNT() AS promoted_admin_count;

COMMIT;