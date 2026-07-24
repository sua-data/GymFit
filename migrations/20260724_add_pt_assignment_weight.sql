-- Adds an optional trainer-defined PT assignment weight in kilograms.
-- Existing assignments remain NULL and are not backfilled.
ALTER TABLE pt_assignment
  ADD COLUMN weight_kg DECIMAL(6,2) NULL
    COMMENT 'PT 숙제에 지정한 사용 중량(kg)'
    AFTER target_minutes,
  ADD CONSTRAINT chk_pt_assignment_weight_kg
    CHECK (weight_kg IS NULL OR weight_kg > 0);

-- Verification: no row should be returned.
SELECT assignment_id, weight_kg
FROM pt_assignment
WHERE weight_kg IS NOT NULL
  AND weight_kg <= 0;
