"""Aggregate a comparison iteration into the numbers the report needs."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "workspace", sys.argv[1] if len(sys.argv) > 1
                    else "compare")
CONFIGS = ("with_skill", "without_skill")


def load(p):
    try:
        return json.load(open(p, encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return None


rows, per_assertion = [], defaultdict(dict)
for entry in sorted(os.listdir(ROOT)):
    d = os.path.join(ROOT, entry)
    if not os.path.isdir(d):
        continue
    for cfg in CONFIGS:
        g = load(os.path.join(d, cfg, "grading.json"))
        t = load(os.path.join(d, cfg, "timing.json")) or {}
        if not g:
            continue
        rows.append({**g, **{"tokens": t.get("total_tokens", 0),
                             "seconds": t.get("total_duration_seconds", 0),
                             "tools": t.get("tool_uses", 0)}})
        for e in g["expectations"]:
            per_assertion[e["text"]][cfg] = \
                per_assertion[e["text"]].get(cfg, []) + [e["passed"]]

summary = {}
for cfg in CONFIGS:
    sel = [r for r in rows if r["configuration"] == cfg]
    if not sel:
        continue
    summary[cfg] = {
        "runs": len(sel),
        "passed_runs": sum(r["verdict"] == "PASS" for r in sel),
        "assertions_passed": sum(r["passed"] for r in sel),
        "assertions_total": sum(r["total"] for r in sel),
        "tokens": sum(r["tokens"] for r in sel),
        "seconds": sum(r["seconds"] for r in sel),
        "docx": sum(r["artifacts"]["docx"] for r in sel),
        "md": sum(r["artifacts"]["md"] for r in sel),
        "png": sum(r["artifacts"]["png"] for r in sel),
        "py": sum(r["artifacts"]["py"] for r in sel),
        "embedded": sum(r["artifacts"]["embedded_images"] for r in sel),
        "prose": sum(r["artifacts"]["prose_chars"] for r in sel),
    }

print("PER-RUN\n" + "-" * 96)
print(f"{'eval':<32}{'config':<15}{'score':>7}{'verdict':>9}"
      f"{'tokens':>10}{'sec':>8}{'docx':>6}{'png':>5}")
for r in rows:
    print(f"{r['eval_id']+' '+r['eval_name']:<32}{r['configuration']:<15}"
          f"{r['passed']:>3}/{r['total']:<3}{r['verdict']:>9}"
          f"{r['tokens']:>10,}{r['seconds']:>8,.0f}"
          f"{r['artifacts']['docx']:>6}{r['artifacts']['png']:>5}")

print("\nTOTALS\n" + "-" * 96)
for cfg, s in summary.items():
    print(f"{cfg:<15} runs {s['passed_runs']}/{s['runs']} passed | "
          f"assertions {s['assertions_passed']}/{s['assertions_total']} "
          f"({s['assertions_passed']/s['assertions_total']:.0%}) | "
          f"{s['tokens']:,} tok | {s['seconds']/60:.1f} min | "
          f"docx {s['docx']} md {s['md']} png {s['png']} py {s['py']}")

if len(summary) == 2:
    a, b = summary["with_skill"], summary["without_skill"]
    print(f"\ndelta: tokens {a['tokens']-b['tokens']:+,} "
          f"({a['tokens']/max(b['tokens'],1):.1f}x)  "
          f"time {(a['seconds']-b['seconds'])/60:+.1f} min "
          f"({a['seconds']/max(b['seconds'],1):.1f}x)  "
          f"assertions "
          f"{a['assertions_passed']/a['assertions_total']-b['assertions_passed']/b['assertions_total']:+.0%}")

print("\nASSERTION DISCRIMINATION\n" + "-" * 96)
disc, nondisc, mixed = [], [], []
for text, cfgs in per_assertion.items():
    w = cfgs.get("with_skill", [])
    o = cfgs.get("without_skill", [])
    if not w or not o:
        continue
    wr, orr = sum(w) / len(w), sum(o) / len(o)
    if wr == 1 and orr == 0:
        disc.append((text, wr, orr))
    elif wr == orr == 1:
        nondisc.append((text, wr, orr))
    else:
        mixed.append((text, wr, orr))

for label, group in (("DISCRIMINATING (skill only)", disc),
                     ("MIXED", mixed),
                     ("NON-DISCRIMINATING (both pass)", nondisc)):
    print(f"\n  {label}")
    for text, wr, orr in sorted(group, key=lambda x: -abs(x[1] - x[2])):
        print(f"    with {wr:>4.0%}  without {orr:>4.0%}   {text[:78]}")

out = os.path.join(ROOT, "analysis.json")
json.dump({"rows": rows, "summary": summary,
           "discriminating": [t for t, _, _ in disc],
           "mixed": [t for t, _, _ in mixed],
           "non_discriminating": [t for t, _, _ in nondisc]},
          open(out, "w", encoding="utf8"), indent=2)
print(f"\nwrote {out}")
