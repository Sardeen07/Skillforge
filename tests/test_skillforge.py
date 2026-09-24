"""Run with:  python3 -m unittest discover tests"""
import importlib.util, json, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin/skills/skillforge/scripts"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


compose = load("compose", "plugin/skills/skillforge/scripts/compose.py")
sf = load("sf", "forge/sf.py")


def mod(name, tokens, applies, group=None, kind="module", status="provisional", **rel):
    return {"name": name, "version": 1, "kind": kind, "mode": "coding", "overlap_group": group or name,
            "applies": applies, "status": status, "score": None, "est_tokens": tokens, "path": f"{name}.md",
            "references": [], "source": None, "requires": [{"target": t} for t in rel.get("requires", [])],
            "mentions": [], "conflicts": [{"target": t} for t in rel.get("conflicts", [])]}


def index(*modules, budget=1000):
    core = mod("core", 100, [], group=None, kind="core")
    core["overlap_group"] = None
    return {"modes": {"coding": {"core": "core", "budget_tokens": budget}}, "modules": [core, *modules]}


def names(result):
    return [m["name"] for m in result[0]]


class ComposeRules(unittest.TestCase):
    def test_no_match_returns_core_only(self):
        r = compose.compose(index(mod("debug", 200, ["bug"])), "coding", ["update README wording"])
        self.assertEqual(names(r), ["core"])
        self.assertEqual(r[3]["misses"], ["update README wording"])

    def test_budget_includes_core_and_is_enforced(self):
        r = compose.compose(index(mod("big", 950, ["bug"])), "coding", ["fix bug"])
        self.assertEqual(names(r), ["core"])  # 100 + 950 > 1000
        self.assertIn("over budget", r[3]["decisions"][0]["result"])

    def test_one_module_per_overlap_group(self):
        idx = index(mod("debug-a", 200, ["bug", "crash"], group="debugging"),
                    mod("debug-b", 150, ["bug"], group="debugging"))
        r = compose.compose(idx, "coding", ["fix bug crash", "another bug"])
        self.assertEqual(names(r), ["core", "debug-a"])

    def test_requires_are_loaded_and_counted(self):
        idx = index(mod("react", 300, ["react"], requires=["js"]), mod("js", 300, ["javascript"]))
        r = compose.compose(idx, "coding", ["react component"])
        self.assertEqual(names(r), ["core", "js", "react"])
        self.assertEqual(r[1], 700)

    def test_requirement_over_budget_skips_whole_group(self):
        idx = index(mod("react", 300, ["react"], requires=["js"]), mod("js", 700, ["javascript"]))
        self.assertEqual(names(compose.compose(idx, "coding", ["react component"])), ["core"])

    def test_conflicts_are_refused(self):
        idx = index(mod("minimal", 200, ["feature"], conflicts=["layers"]), mod("layers", 200, ["architecture"]))
        r = compose.compose(idx, "coding", ["add feature", "architecture cleanup"])
        self.assertEqual(names(r), ["core", "minimal"])

    def test_rejected_and_candidate_modules_are_not_eligible(self):
        idx = index(mod("bad", 100, ["bug"], status="rejected"), mod("new", 100, ["bug"], status="candidate"))
        self.assertEqual(names(compose.compose(idx, "coding", ["fix bug"])), ["core"])

    def test_session_does_not_charge_for_already_emitted(self):
        idx = index(mod("debug", 200, ["bug"]))
        r = compose.compose(idx, "coding", ["fix bug"], emitted={"core@1", "debug@1"})
        self.assertEqual(r[1], 0)


class ImportPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        src = self.tmp / "upstream"
        (src / "skills" / "demo").mkdir(parents=True)
        (src / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\n---\nDemo instructions.\n")
        (src / "LICENSE").write_text("MIT License\n")
        git = lambda *a: subprocess.run(["git", "-C", str(src), *a], check=True, capture_output=True, text=True)
        git("init", "-q"); git("add", "."); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
        self.commit = git("rev-parse", "HEAD").stdout.strip()
        git("config", "uploadpack.allowReachableSHA1InWant", "true")
        sf.DB, sf.SOURCES, sf.LIBRARY = self.tmp / "db.sqlite", self.tmp / "sources", self.tmp / "library"
        sf.ROOT = self.tmp
        (sf.LIBRARY / "core").mkdir(parents=True)
        (sf.LIBRARY / "core" / "coding.md").write_text("Core text.\n")
        self.curation = self.tmp / "coding.json"
        self.curation.write_text(json.dumps({
            "mode": "coding", "budget_tokens": 500,
            "core": {"name": "coding-core", "path": "core/coding.md", "status": "provisional"},
            "modules": [{"name": "demo", "source": {"repo": str(src), "commit": self.commit,
                                                    "path": "skills/demo", "license": "MIT"},
                         "applies": ["demo"], "status": "provisional"}]}))

    def test_migrate_import_export_are_repeatable_and_traceable(self):
        con = sf.connect(sf.DB)
        for _ in range(2):
            sf.migrate(con)
            sf.import_curation(con, self.curation)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM modules").fetchone()[0], 2)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM skill_versions").fetchone()[0], 1)
        self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        row = con.execute("""SELECT v.commit_sha FROM modules m JOIN module_sources ms ON ms.module_id=m.id
                             JOIN skill_versions v ON v.id=ms.skill_version_id WHERE m.name='demo'""").fetchone()
        self.assertEqual(row[0], self.commit)
        self.assertTrue((sf.LIBRARY / "modules" / "demo" / "MODULE.md").exists())
        self.assertFalse((sf.LIBRARY / "modules" / "demo" / "SKILL.md").exists())
        sf.export(con)
        exported = json.loads((sf.LIBRARY / "index.json").read_text())
        self.assertEqual({m["name"] for m in exported["modules"]}, {"coding-core", "demo"})
        self.assertEqual(exported["modules"][1]["source"]["commit"], self.commit)


class Portability(unittest.TestCase):
    """These all passed on Linux and failed on Windows, so they are pinned here."""

    def test_clone_url_expands_only_github_shorthand(self):
        self.assertEqual(sf.clone_url("obra/superpowers"),
                         "https://github.com/obra/superpowers.git")
        self.assertEqual(sf.clone_url("vercel-labs/agent-skills"),
                         "https://github.com/vercel-labs/agent-skills.git")

    def test_clone_url_leaves_urls_and_local_paths_alone(self):
        for repo in ("https://github.com/a/b.git", "file:///srv/a", "/srv/upstream",
                     r"C:\\Users\\dev\\upstream", r"D:\\src\\a\\b"):
            self.assertEqual(sf.clone_url(repo), repo,
                             f"{repo} must be usable as a clone target unchanged")

    def test_library_files_are_utf8(self):
        """A module read as cp1252 crashes the brief instead of degrading."""
        lib = ROOT / "plugin" / "library"
        for f in sorted(lib.rglob("*.md")):
            with self.subTest(file=f.relative_to(lib)):
                f.read_text(encoding="utf-8")  # raises if it is not valid UTF-8

    def test_compose_prints_a_brief_header(self):
        """ab.py and SKILL.md both key off this exact header to prove a brief loaded."""
        out = subprocess.run(
            [sys.executable, str(ROOT / "plugin/skills/skillforge/scripts/compose.py"),
             "--mode", "coding", "--session", str(Path(tempfile.mkdtemp()) / "s.json"),
             "--subtask", "postgres workers block each other in the job queue", "--stack", "postgres"],
            capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertTrue(out.stdout.startswith("# SkillForge brief:"), out.stdout[:200])
        self.assertIn("postgres/lock-skip-locked", out.stdout)


class ReferenceRules(unittest.TestCase):
    """Rules are reached from the reported symptom, and the list stays short.

    Measured: pointing at a directory got zero reference files opened, and the run
    missed keyset pagination while data-pagination.md sat unread inside it.
    """

    def setUp(self):
        import retrieval
        self.r = retrieval
        self.index = json.loads(
            (ROOT / "plugin" / "library" / "index.json").read_text(encoding="utf-8"))
        self.ix = retrieval.Index(retrieval.load_rules(self.index, ROOT / "plugin" / "library"))

    def ids(self, text):
        return [r["id"] for _, r in self.r.rank(self.index, self.ix, [text])[0][1]]

    def test_matches_rules_on_frontmatter_not_filename(self):
        """lock-skip-locked.md is found from "workers", which appears in its tags, not its name."""
        self.assertIn("postgres/lock-skip-locked", self.ids("concurrent workers queue"))

    def test_matches_the_pagination_rule_the_benchmark_missed(self):
        self.assertIn("postgres/data-pagination", self.ids("slow pagination on deep pages"))

    def test_skips_scaffolding_and_caps_the_list(self):
        picked = self.ids("index query schema table lock data")
        self.assertLessEqual(len(picked), 4, "an unbounded list is the folder pointer again")
        self.assertFalse([r for r in picked if "/_" in r], "_template.md and _sections.md are scaffolding")

    def test_no_match_returns_nothing(self):
        self.assertEqual(self.ids("zzzz"), [])


class BenchmarkTasks(unittest.TestCase):
    """A task whose test cannot be failed, or cannot be passed, measures nothing."""

    def test_every_task_has_a_hidden_test_that_fails_on_the_unfixed_fixture(self):
        tasks = sorted(p for p in (ROOT / "benchmarks" / "tasks").iterdir() if p.is_dir())
        self.assertTrue(tasks, "no benchmark tasks found")
        for task in tasks:
            with self.subTest(task=task.name):
                self.assertTrue((task / "task.txt").exists())
                self.assertTrue((task / "test.py").exists())
                try:
                    r = subprocess.run([sys.executable, "test.py"], cwd=task,
                                       capture_output=True, text=True, encoding="utf-8",
                                       timeout=300 if "pgserver" in (task / "test.py").read_text(encoding="utf-8") else 15)
                except subprocess.TimeoutExpired:
                    continue  # binary-search hangs on its own bug; that is a failure
                self.assertNotEqual(r.returncode, 0,
                                    f"{task.name}: the hidden test passes on the unfixed "
                                    f"fixture, so it cannot measure anything")


if __name__ == "__main__":
    unittest.main()
