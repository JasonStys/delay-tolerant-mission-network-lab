-- Immutable restart handoff store by Jason Stys. Tables/triggers: docs/CODE_INDEX.md.
-- Contains only explicit synthetic CLI runs; never exposed by the HTTP application.
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY CHECK(length(id)=64),
    wire TEXT NOT NULL,
    checkpoint TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS checkpoints_no_update BEFORE UPDATE ON checkpoints
BEGIN SELECT RAISE(ABORT,'Checkpoint is immutable'); END;
CREATE TRIGGER IF NOT EXISTS checkpoints_no_delete BEFORE DELETE ON checkpoints
BEGIN SELECT RAISE(ABORT,'Checkpoint is immutable'); END;
