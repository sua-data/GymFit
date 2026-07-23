CREATE TABLE gym_machine (
    machine_id BIGINT NOT NULL AUTO_INCREMENT,
    gym_id BIGINT NOT NULL,
    machine_name VARCHAR(120) NOT NULL,
    body_part VARCHAR(30) NOT NULL,
    brand VARCHAR(100) NULL,
    model_name VARCHAR(120) NULL,
    description TEXT NULL,
    usage_guide TEXT NULL,
    caution TEXT NULL,
    image_url VARCHAR(500) NULL,
    image_storage_path VARCHAR(1000) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_by BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (machine_id),
    CONSTRAINT fk_gym_machine_gym
        FOREIGN KEY (gym_id) REFERENCES gym (gym_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_gym_machine_created_by
        FOREIGN KEY (created_by) REFERENCES users (user_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX ix_gym_machine_gym_active (gym_id, is_active),
    INDEX ix_gym_machine_gym_name (gym_id, machine_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
