ALTER TABLE users
    MODIFY COLUMN account_type
    ENUM('MEMBER', 'TRAINER', 'ADMIN')
    NOT NULL
    COMMENT '계정 유형';
