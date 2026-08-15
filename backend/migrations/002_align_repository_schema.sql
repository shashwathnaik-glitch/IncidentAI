-- Safe Migration to Align SQL Schema with CockroachDBRepository

-- 1. Add name and department to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100);

-- 2. Add reported_by to incidents table
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS reported_by UUID REFERENCES users(id) ON DELETE SET NULL;

-- 3. Add solution_action, notes, and executed_by to solution_attempts table
ALTER TABLE solution_attempts ADD COLUMN IF NOT EXISTS solution_action TEXT;
ALTER TABLE solution_attempts ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE solution_attempts ADD COLUMN IF NOT EXISTS executed_by UUID REFERENCES users(id) ON DELETE SET NULL;

-- 4. Safely populate new columns from old ones if they exist
UPDATE solution_attempts 
SET 
  solution_action = COALESCE(solution_action, solution_text),
  notes = COALESCE(notes, failure_reason),
  executed_by = COALESCE(executed_by, performed_by)
WHERE (solution_action IS NULL AND solution_text IS NOT NULL)
   OR (notes IS NULL AND failure_reason IS NOT NULL)
   OR (executed_by IS NULL AND performed_by IS NOT NULL);

-- 5. Apply the NOT NULL constraint to solution_action
ALTER TABLE solution_attempts ALTER COLUMN solution_action SET NOT NULL;

-- 6. Drop the NOT NULL constraint on solution_text to allow new inserts to omit it
ALTER TABLE solution_attempts ALTER COLUMN solution_text DROP NOT NULL;
