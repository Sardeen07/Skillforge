# Database setup and current limits

**Decision:** the SQLite database is a build-time tool for curating the library. It
is off the runtime path and off the benchmark path, by design, until an ingestion
command exists (see [ROADMAP.md](../ROADMAP.md)).

The installed plugin reads the committed `plugin/library/index.json` and module
files. It does not require a database, API key, Node package install, or network
request to compose a brief. Python 3.10+ is required by this implementation.

The local SQLite database is for building and curating the library:

```sh
node forge/py.mjs forge/sf.py migrate
node forge/py.mjs forge/sf.py import forge/curation/coding.json
node forge/py.mjs forge/sf.py list
node forge/py.mjs forge/sf.py trace postgres
node forge/py.mjs forge/sf.py export
```

Run from the repository root. `migrate` creates/upgrades `data/skillforge.db`.
`import` fetches the exact commits in the curation file and needs network access;
it copies modules while retaining source/license metadata. `export` writes the
runtime JSON index. Import/export are repeatable; don't use them to overwrite
uncommitted intentional changes in imported source modules.

For your first experiment, the committed index and modules are already sufficient.
Run `npm test`, `npm run retrieval`, then the dry-run instructions in
`BENCHMARK_PROTOCOL.md`. No database migration is necessary for those commands.

`ab.py` now saves auditable JSONL, but does **not** insert its attempts into SQLite's
`runs` table. The existing schema is not an automatic benchmark ingestion pipeline.
Keep JSONL and source hashes with the experiment. A future ingestion command should
validate task/module/model versions and preserve errors and unknown costs before
updating quality scores. Never manually fill score fields with invented values.
