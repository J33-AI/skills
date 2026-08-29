"""Grade completed eval runs against their assertions.

    python grade_evals.py --iteration iteration-1
    python grade_evals.py --iteration iteration-1 --only e06
    python grade_evals.py --iteration iteration-1 --json
    python grade_evals.py --list-checks

Writes grading.json into each run directory and prints a summary table.

Pass/fail per eval comes from `pass_criteria` in evals.json:
  required   assertion ids that must ALL pass — one failure fails the eval
  min_score  the fraction of all assertions that must pass

An eval passes when both hold. That split matters: `required` covers the things
that make the document wrong (fabricated tables, missing artefacts), while
`min_score` covers overall quality without letting one soft miss fail the run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.checks import CHECKS, collect, run_check          # noqa: E402

WORKSPACE = os.path.join(HERE, "workspace")

# Windows consoles default to cp1252 and choke on the arrows and ≥ signs the
# evidence strings use. Force UTF-8 and degrade gracefully if that is refused.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def load_suite() -> dict:
    with open(os.path.join(HERE, "evals.json"), encoding="utf8") as fh:
        return json.load(fh)


def resolve(assertions: list, shared: dict) -> list[dict]:
    """Expand shared assertion names into full definitions."""
    out = []
    for a in assertions:
        if isinstance(a, str):
            if a not in shared:
                raise KeyError(f"unknown shared assertion '{a}'")
            out.append({"id": a, **shared[a]})
        else:
            out.append(a)
    return out


def grade_run(run_dir: str, assertions: list[dict]) -> dict:
    outputs = os.path.join(run_dir, "outputs")
    data = collect(outputs)
    expectations = []
    for a in assertions:
        passed, evidence = run_check(a["check"], data)
        expectations.append({"id": a["id"], "text": a["text"],
                             "passed": passed, "evidence": evidence})
    passed_n = sum(e["passed"] for e in expectations)
    return {
        "expectations": expectations,
        "passed": passed_n,
        "total": len(expectations),
        "pass_rate": round(passed_n / max(len(expectations), 1), 3),
        "artifacts": {
            "docx": len(data["docx"]), "md": len(data["md"]),
            "png": len(data["png"]), "py": len(data["py"]),
            "embedded_images": data["embedded_images"],
            "prose_chars": len(data["text"]),
        },
    }


def verdict(grade: dict, criteria: dict) -> tuple[bool, str]:
    required = criteria.get("required", [])
    min_score = criteria.get("min_score", 0.0)
    by_id = {e["id"]: e for e in grade["expectations"]}
    failed_required = [r for r in required
                       if not by_id.get(r, {"passed": False})["passed"]]
    if failed_required:
        return False, f"required assertion(s) failed: {', '.join(failed_required)}"
    if grade["pass_rate"] < min_score:
        return False, (f"score {grade['pass_rate']:.0%} below the "
                       f"{min_score:.0%} threshold")
    return True, f"{grade['pass_rate']:.0%}, all required assertions passed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iteration", default="iteration-1")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list-checks", action="store_true")
    args = ap.parse_args()

    if args.list_checks:
        print("Available check types (lib/checks.py):\n")
        for name, fn in sorted(CHECKS.items()):
            doc = (fn.__doc__ or "").strip().split("\n")[0]
            print(f"  {name:<20} {doc}")
        return 0

    suite = load_suite()
    shared = suite["shared_assertions"]
    by_id = {e["id"]: e for e in suite["evals"]}
    root = os.path.join(WORKSPACE, args.iteration)
    if not os.path.isdir(root):
        print(f"no runs found at {root} — run run_evals.py first",
              file=sys.stderr)
        return 1

    results = []
    for entry in sorted(os.listdir(root)):
        meta_path = os.path.join(root, entry, "eval_metadata.json")
        if not os.path.isfile(meta_path):
            continue
        meta = json.load(open(meta_path, encoding="utf8"))
        if args.only and meta["eval_id"] not in args.only \
                and meta["eval_name"] not in args.only:
            continue
        ev = by_id.get(meta["eval_id"])
        if ev is None:
            continue
        assertions = resolve(ev["assertions"], shared)

        for cfg in ("with_skill", "without_skill"):
            run_dir = os.path.join(root, entry, cfg)
            if not os.path.isdir(os.path.join(run_dir, "outputs")):
                continue
            grade = grade_run(run_dir, assertions)
            ok, why = verdict(grade, ev["pass_criteria"])
            payload = {
                "eval_id": meta["eval_id"],
                "eval_name": meta["eval_name"],
                "doc_type": meta["doc_type"],
                "configuration": cfg,
                "verdict": "PASS" if ok else "FAIL",
                "verdict_reason": why,
                **grade,
            }
            with open(os.path.join(run_dir, "grading.json"), "w",
                      encoding="utf8") as fh:
                json.dump(payload, fh, indent=2)
            results.append(payload)

    if not results:
        print("nothing graded — are there outputs in the run directories?",
              file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    width = max(len(f"{r['eval_id']} {r['eval_name']}") for r in results) + 2
    print(f"{'eval':<{width}} {'config':<15} {'score':>7}  {'':<6} reason")
    print("-" * (width + 60))
    for r in results:
        label = f"{r['eval_id']} {r['eval_name']}"
        mark = "PASS" if r["verdict"] == "PASS" else "FAIL"
        print(f"{label:<{width}} {r['configuration']:<15} "
              f"{r['passed']:>2}/{r['total']:<4} {mark:<6} {r['verdict_reason']}")

    for r in results:
        failed = [e for e in r["expectations"] if not e["passed"]]
        if failed:
            print(f"\n{r['eval_id']} {r['eval_name']} [{r['configuration']}] "
                  f"— failed assertions:")
            for e in failed:
                print(f"    {e['id']:<22} {e['text']}")
                print(f"    {'':<22} → {e['evidence']}")

    passes = sum(r["verdict"] == "PASS" for r in results)
    print(f"\n{passes}/{len(results)} run(s) passed")
    return 0 if passes == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
