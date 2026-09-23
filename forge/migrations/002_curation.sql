-- Curated modules, their sources and relations, mode configs, compositions,
-- and richer benchmark runs. Column additions to existing tables are applied
-- by forge/sf.py (SQLite has no ADD COLUMN IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS modules (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  version       INTEGER NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('core', 'module')),
  mode          TEXT NOT NULL,
  capability    TEXT,
  overlap_group TEXT,
  applies       TEXT NOT NULL DEFAULT '[]',   -- JSON list of keywords / stack names
  path          TEXT NOT NULL,                -- relative to plugin/library/
  content_hash  TEXT NOT NULL,
  est_tokens    INTEGER NOT NULL,             -- estimate (chars / 4), not a measured count
  status        TEXT NOT NULL CHECK (status IN ('candidate', 'provisional', 'preferred', 'rejected')),
  compacted     INTEGER NOT NULL DEFAULT 0,   -- 0 = original source text, 1 = our rewrite
  score         REAL,                         -- NULL until benchmarks exist
  notes         TEXT,
  created_at    TEXT NOT NULL,
  UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS module_sources (
  module_id        INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  skill_version_id INTEGER NOT NULL REFERENCES skill_versions(id),
  PRIMARY KEY (module_id, skill_version_id)
);

-- kind: requires = must load together; mentions = text refers to it (soft);
-- conflicts = never load together.
CREATE TABLE IF NOT EXISTS module_relations (
  module_id   INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  kind        TEXT NOT NULL CHECK (kind IN ('requires', 'mentions', 'conflicts')),
  target_name TEXT NOT NULL,
  reason      TEXT,
  PRIMARY KEY (module_id, kind, target_name)
);

CREATE TABLE IF NOT EXISTS mode_configs (
  mode          TEXT PRIMARY KEY,
  core_module   TEXT NOT NULL,
  budget_tokens INTEGER NOT NULL,
  notes         TEXT
);

CREATE TABLE IF NOT EXISTS compositions (
  id              INTEGER PRIMARY KEY,
  mode            TEXT NOT NULL,
  arm             TEXT NOT NULL,   -- none | native | skillforge-original | skillforge-compact
  module_versions TEXT NOT NULL,   -- JSON list of "name@version"
  created_at      TEXT NOT NULL,
  UNIQUE (mode, arm, module_versions)
);
