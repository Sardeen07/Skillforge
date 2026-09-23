CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY, repo TEXT, path TEXT, name TEXT, description TEXT,
  license TEXT, stars INTEGER, first_seen TEXT, UNIQUE(repo, path));
CREATE TABLE IF NOT EXISTS skill_versions (id INTEGER PRIMARY KEY, skill_id INTEGER REFERENCES skills(id),
  commit_sha TEXT, content_hash TEXT, risk_flags TEXT, crawled_at TEXT);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, name TEXT, category TEXT, repo_path TEXT, test_cmd TEXT, version INTEGER);
CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, skill_version_ids TEXT, task_id INTEGER REFERENCES tasks(id),
  model TEXT, passed INTEGER, tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, tool_calls INTEGER,
  duration_s REAL, started_at TEXT);
CREATE TABLE IF NOT EXISTS scores (skill_version_id INTEGER, task_category TEXT, success_delta REAL,
  token_delta REAL, cost_delta REAL, model TEXT);
