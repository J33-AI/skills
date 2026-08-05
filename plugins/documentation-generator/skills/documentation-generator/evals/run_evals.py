"""Prepare eval runs and print the agent prompts to execute.

This does not call a model itself — it prepares fixtures, creates the run
directories, and emits the exact task prompt for each run. Paste those into
whatever executes them (subagents, `claude -p`, a colleague), then point
grade_evals.py at the workspace.

    python run_evals.py --list
    python run_evals.py --all
    python run_evals.py --only e06 e09          # the honesty edge cases
    python run_evals.py --tag edge              # objective contains EDGE CASE
    python run_evals.py --all --with-baseline   # also emit no-skill prompts
    python run_evals.py --all --json            # machine-readable

Runs land in  evals/workspace/<iteration>/<eval-id>-<name>/<config>/outputs/
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REPO_ROOT = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
FIXTURES = os.path.join(HERE, "fixtures")
WORKSPACE = os.path.join(HERE, "workspace")

sys.path.insert(0, HERE)
from make_fixtures import FIXTURES as FIXTURE_DEFS, write as write_fixture  # noqa: E402


def load_evals() -> dict:
    with open(os.path.join(HERE, "evals.json"), encoding="utf8") as fh:
        return json.load(fh)


def repo_path(ev: dict) -> str | None:
    """Where the eval's repository lives, preparing it if it is a fixture."""
    spec = ev["repo"]
    if "fixture" in spec:
        name = spec["fixture"]
        path = os.path.join(FIXTURES, name)
        if not os.path.isdir(path):
            write_fixture(name)
        return path
    path = os.path.join(REPO_ROOT, spec["path"])
    if not os.path.isdir(path):
        return None
    return path


def build_prompt(ev: dict, repo: str, out_dir: str, with_skill: bool) -> str:
    skill_line = (
        f"- Skill path: {os.path.join(SKILL, 'SKILL.md')}\n"
        f"  Read that SKILL.md first and follow it. Supporting files sit beside "
        f"it (prompt.md, references/, templates/, scripts/) — read the ones it "
        f"points you to.\n"
        if with_skill else
        "- No skill is provided. Use your own judgement.\n")

    return (
        f"Execute this task.\n\n"
        f"{skill_line}\n"
        f"- Task (the user's request, verbatim): \"{ev['prompt']}\"\n\n"
        f"- Repository to document: {repo}\n"
        f"- Save every output to: {out_dir}\n"
        f"  Include the documents, any generated figures, and any scripts you "
        f"wrote.\n\n"
        f"Notes:\n"
        f"- Do not ask clarifying questions; decide and proceed.\n"
        f"- Work autonomously to completion.\n"
        f"- Report in 3-5 sentences what you produced and anything notable you "
        f"found in the code.\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--tag", default=None,
                    help="substring match against the objective, e.g. 'EDGE'")
    ap.add_argument("--iteration", default="iteration-1")
    ap.add_argument("--with-baseline", action="store_true",
                    help="also emit prompts for a no-skill comparison run")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    suite = load_evals()
    evals = suite["evals"]

    if args.list:
        width = max(len(e["id"]) + len(e["name"]) for e in evals) + 3
        print(f"{'id / name':<{width}} {'type':<26} objective")
        print("-" * 118)
        for e in evals:
            label = f"{e['id']}  {e['name']}"
            optional = e["repo"].get("optional")
            missing = optional and repo_path(e) is None
            note = "  [skipped — repo not present]" if missing else ""
            print(f"{label:<{width}} {e['doc_type']:<26} "
                  f"{e['objective'][:60]}{note}")
        return 0

    selected = evals
    if args.only:
        selected = [e for e in evals if e["id"] in args.only
                    or e["name"] in args.only]
    elif args.tag:
        selected = [e for e in evals
                    if args.tag.lower() in e["objective"].lower()]
    elif not args.all:
        ap.error("choose --all, --only, --tag or --list")

    jobs = []
    for ev in selected:
        repo = repo_path(ev)
        if repo is None:
            print(f"skipping {ev['id']} — repository "
                  f"{ev['repo'].get('path')} not present", file=sys.stderr)
            continue
        base = os.path.join(WORKSPACE, args.iteration,
                            f"{ev['id']}-{ev['name']}")
        configs = ["with_skill"] + (["without_skill"] if args.with_baseline
                                    else [])
        for cfg in configs:
            out_dir = os.path.join(base, cfg, "outputs")
            os.makedirs(out_dir, exist_ok=True)
            jobs.append({
                "eval_id": ev["id"],
                "eval_name": ev["name"],
                "configuration": cfg,
                "repo": repo,
                "outputs": out_dir,
                "prompt": build_prompt(ev, repo, out_dir,
                                       cfg == "with_skill"),
            })
        # metadata the grader needs
        with open(os.path.join(base, "eval_metadata.json"), "w",
                  encoding="utf8") as fh:
            json.dump({
                "eval_id": ev["id"],
                "eval_name": ev["name"],
                "doc_type": ev["doc_type"],
                "objective": ev["objective"],
                "prompt": ev["prompt"],
                "repo": repo,
                "expected_output": ev["expected_output"],
                "assertions": ev["assertions"],
                "pass_criteria": ev["pass_criteria"],
            }, fh, indent=2)

    if args.json:
        print(json.dumps(jobs, indent=2))
        return 0

    print(f"Prepared {len(jobs)} run(s) under "
          f"{os.path.join(WORKSPACE, args.iteration)}\n")
    for i, job in enumerate(jobs, 1):
        print("=" * 78)
        print(f"RUN {i}/{len(jobs)}   {job['eval_id']}  {job['eval_name']}  "
              f"[{job['configuration']}]")
        print("=" * 78)
        print(job["prompt"])
    print("=" * 78)
    print("\nWhen the runs are finished:\n")
    print(f"    python grade_evals.py --iteration {args.iteration}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
