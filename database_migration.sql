-- Database Migration: Create new student_profiles table with JSONB support
-- This migration preserves the old table and creates a brand new one

-- Step 1: Rename the existing table to legacy
ALTER TABLE student_profiles RENAME TO student_profiles_legacy;

-- Step 2: Create new student_profiles table with JSONB structure
CREATE TABLE student_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id TEXT NOT NULL,
    profile_summary JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 3: Create unique constraint on student_id (one profile per student for MVP)
ALTER TABLE student_profiles ADD CONSTRAINT unique_student_profile UNIQUE (student_id);

-- Step 3b: Create index on student_id for fast lookups (already unique)
CREATE INDEX idx_student_profiles_student_id ON student_profiles (student_id);

-- Step 4: Create GIN index for efficient JSON queries
CREATE INDEX idx_student_profiles_summary_gin ON student_profiles USING GIN (profile_summary);

-- Step 5: Create index on timestamp for chronological queries
CREATE INDEX idx_student_profiles_timestamp ON student_profiles (timestamp DESC);

-- Step 6: Optionally migrate existing data from legacy table (if any exists)
-- This wraps legacy text profiles in structured JSON format
INSERT INTO student_profiles (student_id, profile_summary, timestamp)
SELECT 
    student_id,
    CASE 
        WHEN profile_summary IS NOT NULL AND profile_summary != '' 
        THEN jsonb_build_object('legacy_profile', profile_summary)
        ELSE '{}'::jsonb
    END as profile_summary,
    timestamp
FROM student_profiles_legacy
WHERE student_id IS NOT NULL;

-- Verification queries
-- SELECT 'Legacy table count' as info, COUNT(*) as count FROM student_profiles_legacy;
-- SELECT 'New table count' as info, COUNT(*) as count FROM student_profiles;
-- SELECT student_id, profile_summary, timestamp FROM student_profiles ORDER BY timestamp DESC LIMIT 3;