#!/usr/bin/env python3
"""SkillForge library builder.

  python3 forge/sf.py migrate                       create/upgrade data/skillforge.db
  python3 forge/sf.py import forge/curation/coding.json
                                                    pin sources, copy modules, record them
  python3 forge/sf.py list                          show modules and their status
  python3 forge/sf.py trace <module>                module -> exact source repo/commit/path
  python3 forge/sf.py export                        write plugin/library/index.json

Every command is safe to repeat. Token counts are estimates (characters / 4).
"""
import argparse, fnmatch, hashlib, json, shutil, sqlite3, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "skillforge.db"
SOURCES = ROOT / "data" / "sources"
LIBRARY = ROOT / "plugin" / "library"
MIGRATIONS = ROOT / "forge" / "migrations"
EXPORT_STATUSES = ("provisional", "preferred")

# Columns added to tables that already exist (SQLite lacks ADD COLUMN IF NOT EXISTS).
ADDED_COLUMNS = {
    "skill_versions": {"local_path": "TEXT"},
    "tasks": {"suite": "TEXT"},  # dev | heldout
    "runs": {"composition_id": "INTEGER REFERENCES compositions(id)", "arm": "TEXT",
             "status": "TEXT",  # pass | fail | harness_error (NULL = unknown)
             "task_version": "INTEGER", "repo_revision": "TEXT", "settings": "TEXT",
             "cached_tokens": "INTEGER", "activated": "INTEGER", "artifact_path": "TEXT"},
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def est_tokens(text):
    return max(1, len(text) // 4)


def connect(path=DB):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


# ---------------------------------------------------------------- migrate
def migrate(con):
    version = con.execute("PRAGMA user_version").fetchone()[0]
    files = sorted(MIGRATIONS.glob("*.sql"))
    for f in files:
        n = int(f.name.split("_")[0])
        if n <= version:
            continue
        con.executescript(f.read_text())
        con.execute(f"PRAGMA user_version = {n}")
        print(f"applied {f.name}")
    for table, cols in ADDED_COLUMNS.items():
        have = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
        for col, kind in cols.items():
            if col not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")
    con.commit()
    print(f"database at schema version {con.execute('PRAGMA user_version').fetchone()[0]}: {DB.relative_to(ROOT)}")


# ---------------------------------------------------------------- import
def clone_url(repo):
    return repo if repo.startswith(("/", "file:", "http")) else f"https://github.com/{repo}.git"


def fetch_source(repo, commit):
    """Check out repo at an exact commit under data/sources (reused if present)."""
    dest = SOURCES / f"{repo.strip('/').replace('/', '__')}@{commit[:12]}"
    if (dest / ".git").exists():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(["git", "-C", str(dest), *a], check=True, capture_output=True, text=True)
    run("init", "-q")
    run("remote", "add", "origin", clone_url(repo))
    run("fetch", "-q", "--depth", "1", "origin", commit)
    run("checkout", "-q", "FETCH_HEAD")
    head = run("rev-parse", "HEAD").stdout.strip()
    if head != commit:
        sys.exit(f"{repo}: expected commit {commit}, got {head}")
    return dest


def copy_module(src_dir, dest_dir, exclude):
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    for f in sorted(src_dir.rglob("*")):
        rel = f.relative_to(src_dir)
        if f.is_dir() or any(fnmatch.fnmatch(rel.name, pat) for pat in exclude):
            continue
        # Renamed so Claude Code never registers library modules as separate skills.
        target = dest_dir / ("MODULE.md" if str(rel) == "SKILL.md" else rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
    return dest_dir / "MODULE.md"


def upsert_module(con, spec, kind, mode, path, text, skill_version_id=None):
    digest = hashlib.sha256(text.encode()).hexdigest()
    row = con.execute("SELECT id, version FROM modules WHERE name=? AND content_hash=?",
                      (spec["name"], digest)).fetchone()
    if row:
        module_id = row["id"]
        con.execute("UPDATE modules SET status=?, applies=?, capability=?, overlap_group=?, notes=? WHERE id=?",
                    (spec.get("status", "candidate"), json.dumps(spec.get("applies", [])),
                     spec.get("capability"), spec.get("overlap_group"), spec.get("notes"), module_id))
    else:
        prev = con.execute("SELECT MAX(version) FROM modules WHERE name=?", (spec["name"],)).fetchone()[0]
        module_id = con.execute(
            """INSERT INTO modules (name, version, kind, mode, capability, overlap_group, applies, path,
                                    content_hash, est_tokens, status, compacted, notes, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (spec["name"], (prev or 0) + 1, kind, mode, spec.get("capability"), spec.get("overlap_group"),
             json.dumps(spec.get("applies", [])), path, digest, est_tokens(text),
             spec.get("status", "candidate"), int(spec.get("compacted", False)), spec.get("notes"), now())).lastrowid
    con.execute("DELETE FROM module_relations WHERE module_id=?", (module_id,))
    for kind_name in ("requires", "mentions", "conflicts"):
        for rel in spec.get(kind_name, []):
            rel = rel if isinstance(rel, dict) else {"target": rel}
            con.execute("INSERT INTO module_relations VALUES (?,?,?,?)",
                        (module_id, kind_name, rel["target"], rel.get("reason")))
    if skill_version_id:
        con.execute("INSERT OR IGNORE INTO module_sources VALUES (?,?)", (module_id, skill_version_id))
    return module_id


def record_source(con, src, local_path):
    con.execute("""INSERT INTO skills (repo, path, name, license, stars, first_seen) VALUES (?,?,?,?,NULL,?)
                   ON CONFLICT(repo, path) DO UPDATE SET license=excluded.license""",
                (src["repo"], src["path"], Path(src["path"]).name, src.get("license"), now()))
    skill_id = con.execute("SELECT id FROM skills WHERE repo=? AND path=?", (src["repo"], src["path"])).fetchone()[0]
    text = (local_path / "SKILL.md").read_text()
    digest = hashlib.sha256(text.encode()).hexdigest()
    row = con.execute("SELECT id FROM skill_versions WHERE skill_id=? AND commit_sha=?",
                      (skill_id, src["commit"])).fetchone()
    if row:
        return row["id"]
    return con.execute("""INSERT INTO skill_versions (skill_id, commit_sha, content_hash, crawled_at, local_path)
                          VALUES (?,?,?,?,?)""",
                       (skill_id, src["commit"], digest, now(), str(local_path.relative_to(ROOT)))).lastrowid


def import_curation(con, curation_path):
    cur = json.loads(Path(curation_path).read_text())
    mode = cur["mode"]
    core = cur["core"]
    core_text = (LIBRARY / core["path"]).read_text()
    upsert_module(con, core, "core", mode, core["path"], core_text)
    con.execute("""INSERT INTO mode_configs (mode, core_module, budget_tokens) VALUES (?,?,?)
                   ON CONFLICT(mode) DO UPDATE SET core_module=excluded.core_module,
                   budget_tokens=excluded.budget_tokens""", (mode, core["name"], cur["budget_tokens"]))
    for spec in cur["modules"]:
        src = spec["source"]
        checkout = fetch_source(src["repo"], src["commit"])
        src_dir = checkout / src["path"]
        if not (src_dir / "SKILL.md").exists():
            sys.exit(f"{spec['name']}: no SKILL.md at {src['repo']}/{src['path']}")
        sv_id = record_source(con, src, src_dir)
        dest = LIBRARY / "modules" / spec["name"]
        main = copy_module(src_dir, dest, spec.get("exclude", []))
        (dest / "SOURCE.json").write_text(json.dumps(
            {"repo": src["repo"], "commit": src["commit"], "path": src["path"], "license": src.get("license"),
             "modified": False, "note": "Original text; SKILL.md renamed to MODULE.md"}, indent=2) + "\n")
        repo_license = checkout / "LICENSE"
        if repo_license.exists() and not any(dest.glob("LICENSE*")):
            shutil.copy2(repo_license, dest / "LICENSE")
        upsert_module(con, spec, "module", mode, str(main.relative_to(LIBRARY)), main.read_text(), sv_id)
        print(f"imported {spec['name']:32} {src['repo']}@{src['commit'][:7]}")
    con.commit()


# ---------------------------------------------------------------- inspect
def latest_modules(con, statuses=None):
    rows = con.execute("""SELECT m.* FROM modules m
                          JOIN (SELECT name, MAX(version) v FROM modules GROUP BY name) l
                            ON l.name = m.name AND l.v = m.version ORDER BY m.kind, m.name""").fetchall()
    return [r for r in rows if statuses is None or r["status"] in statuses]


def list_modules(con):
    for r in latest_modules(con):
        print(f"{r['kind']:6} {r['name']:32} v{r['version']}  {r['status']:11} group={r['overlap_group'] or '-':12} "
              f"~{r['est_tokens']} tok (est)")


def trace(con, name):
    m = con.execute("SELECT * FROM modules WHERE name=? ORDER BY version DESC LIMIT 1", (name,)).fetchone()
    if not m:
        sys.exit(f"no module named {name}")
    print(f"{m['name']} v{m['version']} ({m['status']}) -> plugin/library/{m['path']}  sha256 {m['content_hash'][:12]}")
    srcs = con.execute("""SELECT s.repo, s.path, s.license, v.commit_sha FROM module_sources ms
                          JOIN skill_versions v ON v.id = ms.skill_version_id
                          JOIN skills s ON s.id = v.skill_id WHERE ms.module_id=?""", (m["id"],)).fetchall()
    for s in srcs:
        print(f"  source: {s['repo']}/{s['path']} @ {s['commit_sha']} ({s['license']})")
    if not srcs:
        print(f"  source: authored ({m['notes'] or 'no notes'})")
    for r in con.execute("SELECT kind, target_name, reason FROM module_relations WHERE module_id=?", (m["id"],)):
        print(f"  {r['kind']}: {r['target_name']}  {r['reason'] or ''}")


# ---------------------------------------------------------------- export
def export(con):
    modules = []
    for m in latest_modules(con, EXPORT_STATUSES):
        rels = {k: [] for k in ("requires", "mentions", "conflicts")}
        for r in con.execute("SELECT kind, target_name, reason FROM module_relations WHERE module_id=?", (m["id"],)):
            rels[r["kind"]].append({"target": r["target_name"], "reason": r["reason"]})
        folder = (LIBRARY / m["path"]).parent
        refs = sorted(str(p.relative_to(LIBRARY)) for p in folder.rglob("*")
                      if p.is_file() and p.name not in ("MODULE.md", "SOURCE.json", "LICENSE")
                      and not p.name.startswith("LICENSE")) if m["kind"] == "module" else []
        source = json.loads((folder / "SOURCE.json").read_text()) if (folder / "SOURCE.json").exists() else None
        modules.append({
            "name": m["name"], "version": m["version"], "kind": m["kind"], "mode": m["mode"],
            "capability": m["capability"], "overlap_group": m["overlap_group"],
            "applies": json.loads(m["applies"]), "status": m["status"], "score": m["score"],
            "est_tokens": m["est_tokens"], "path": m["path"], "references": refs, "source": source, **rels})
    modes = {r["mode"]: {"core": r["core_module"], "budget_tokens": r["budget_tokens"]}
             for r in con.execute("SELECT * FROM mode_configs")}
    index = {"generated_at": now(), "token_estimate": "characters / 4 (estimate, not a measured token count)",
             "modes": modes, "modules": modules}
    (LIBRARY / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(f"exported {len(modules)} modules to plugin/library/index.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    imp = sub.add_parser("import"); imp.add_argument("curation")
    sub.add_parser("list")
    tr = sub.add_parser("trace"); tr.add_argument("module")
    sub.add_parser("export")
    args = ap.parse_args()
    con = connect()
    if args.cmd == "migrate":
        migrate(con)
    else:
        if con.execute("PRAGMA user_version").fetchone()[0] < 2:
            sys.exit("Run `python3 forge/sf.py migrate` first.")
        {"import": lambda: import_curation(con, args.curation), "list": lambda: list_modules(con),
         "trace": lambda: trace(con, args.module), "export": lambda: export(con)}[args.cmd]()


if __name__ == "__main__":
    main()
