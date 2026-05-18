from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


SRC = Path(__file__).resolve().parent / "phase1_boolean_matrix_v1.jsonl"
OUT_CSV = Path(__file__).resolve().parent / "phase1_boolean_feature_stats.csv"
OUT_JSON = Path(__file__).resolve().parent / "phase1_boolean_feature_stats.json"

FEATURE_ORDER = [
    "single_plaintiff","multiple_plaintiffs","single_defendant","multiple_defendants",
    "negligence","gross_negligence","joint_liability","prior_criminal",
    "head_neck","trunk","extremities","psych_other",
    "medical_rehab","lost_income","non_pecuniary","care_other",
]


def main() -> None:
    counts = Counter()
    total = 0
    review_total = 0

    with SRC.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total += 1
            matrix = rec["boolean_matrix"]
            flat = {}
            flat.update(matrix["litigants"])
            flat.update(matrix["fact"])
            flat.update(matrix["injury"])
            flat.update(matrix["compensation"])
            for k, v in flat.items():
                counts[k] += int(v)
            if rec.get("review_flags"):
                review_total += 1

    print(f"total_cases: {total}")
    print(f"cases_with_review_flags: {review_total}")
    print()
    rows = []
    for key in FEATURE_ORDER:
        val = counts[key]
        ratio = (val / total * 100) if total else 0
        print(f"{key:24s} {val:5d}  ({ratio:6.2f}%)")
        rows.append({
            "feature": key,
            "count": val,
            "ratio_pct": round(ratio, 4),
        })

    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["feature", "count", "ratio_pct"])
        writer.writeheader()
        writer.writerows(rows)

    OUT_JSON.write_text(
        json.dumps(
            {
                "total_cases": total,
                "cases_with_review_flags": review_total,
                "features": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print()
    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
