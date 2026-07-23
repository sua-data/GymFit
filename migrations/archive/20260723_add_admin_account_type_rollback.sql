UPDATE users
SET account_type = 'MEMBER'
WHERE account_type = 'ADMIN';

ALTER TABLE users
    MODIFY COLUMN account_type
    ENUM('MEMBER', 'TRAINER')
    NOT NULL
    COMMENT '계정 유형';
