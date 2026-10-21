-- Immutable local simulation history by Jason Stys. Tables/triggers: docs/CODE_INDEX.md.
-- Explicit CLI-only persistence; SQL parameters and content hashing precede insertion.
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY CHECK(length(id)=64),
    scenario TEXT NOT NULL,
    report_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS runs_no_update BEFORE UPDATE ON runs
BEGIN SELECT RAISE(ABORT,'History is immutable'); END;
CREATE TRIGGER IF NOT EXISTS runs_no_delete BEFORE DELETE ON runs
BEGIN SELECT RAISE(ABORT,'History is immutable'); END;
