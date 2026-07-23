START TRANSACTION;

ALTER TABLE `workout_plan`
  DROP FOREIGN KEY `fk_workout_plan_recommendation_item`,
  DROP CONSTRAINT `ck_workout_plan_source`,
  DROP INDEX `uq_workout_plan_recommendation_item`,
  DROP COLUMN `plan_source`,
  DROP COLUMN `recommendation_item_id`;

DROP TABLE IF EXISTS `routine_recommendation_item`;
DROP TABLE IF EXISTS `routine_recommendation`;

COMMIT;

