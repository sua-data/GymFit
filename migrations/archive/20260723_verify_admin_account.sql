SELECT account_type, COUNT(*) AS account_count
FROM users
GROUP BY account_type
ORDER BY account_type;

SELECT user_id, email, login_provider, is_active, created_at, updated_at
FROM users
WHERE account_type = 'ADMIN'
ORDER BY user_id;
