#!/usr/bin/env python3
"""Pick the best library fragments for a task and print one compact brief."""
import argparse, json, re
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "library"

def words(text):
    return set(re.findall(r"[a-z]+", text.lower()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="coding")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("task")
    args = ap.parse_args()

    index = json.loads((LIB / "index.json").read_text())["skills"]
    mode_file = LIB / "modes" / f"{args.mode}.json"
    defaults = json.loads(mode_file.read_text())["defaults"] if mode_file.exists() else []

    task = words(args.task)
    candidates = [s for s in index if args.mode in s["modes"] and s["risk"] == "low"]
    for s in candidates:
        overlap = len(task & words(" ".join(s["tags"]) + " " + s["description"]))
        s["_rank"] = overlap * (1 + s.get("score", 0))
    picked = [s for s in sorted(candidates, key=lambda s: -s["_rank"]) if s["_rank"] > 0][: args.top]
    picked += [s for s in index if s["id"] in defaults and s not in picked]

    print(f"# SkillForge brief ({args.mode})\n")
    for s in picked:
        if s["type"] == "external":
            print(f"- Recommended plugin: {s['id']} ({s['install']})")
        else:
            print(f"## {s['id']}\n{(LIB / s['path']).read_text().strip()}\n")

if __name__ == "__main__":
    main()
