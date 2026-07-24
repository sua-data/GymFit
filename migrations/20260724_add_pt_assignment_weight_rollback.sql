-- Removes the optional PT assignment weight field.
ALTER TABLE pt_assignment
  DROP CONSTRAINT chk_pt_assignment_weight_kg,
  DROP COLUMN weight_kg;
