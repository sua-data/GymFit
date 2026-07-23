ALTER TABLE gym
    ADD COLUMN phone VARCHAR(50) NULL AFTER address,
    ADD COLUMN place_url VARCHAR(500) NULL AFTER phone,
    ADD COLUMN category_name VARCHAR(255) NULL AFTER place_url;
