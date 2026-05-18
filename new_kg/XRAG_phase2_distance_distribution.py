"""
XRAG Phase 2: distance distribution analysis

Purpose:
- Inspect the empirical distribution of d(i,j)
- Help choose low / medium / high distance thresholds from data
- Avoid arbitrary threshold selection

Outputs:
- distance_distribution_summary.csv
- distance_distribution_summary.json
- threshold_recommendations.csv
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

import numpy as np

from XRAG_phase2_experiment_graphs import build_case_arrays, build_experiments


BASE_DIR = Path(__file__).resolve().parent
OUT_SUMMARY_CSV = BASE_DIR / "distance_distribution_summary.csv"
OUT_SUMMARY_JSON = BASE_DIR / "distance_distribution_summary.json"
OUT_RECOMMEND_CSV = BASE_DIR / "threshold_recommendations.csv"


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def quantile_value(values: np.ndarray, q: float) -> float:
    return float(np.quantile(values, q))


def ratio_le(values: np.ndarray, threshold: float) -> float:
    return float(np.mean(values <= threshold))


def main() -> None:
    arrays = build_case_arrays()
    fact_values = arrays["fact_values"]
    injury_values = arrays["injury_values"]
    comp_values = arrays["comp_values"]
    n = len(arrays["case_ids"])

    # Upper triangle without diagonal: one sample per unordered pair.
    tri_i, tri_j = np.triu_indices(n, k=1)

    fact_diff = np.abs(fact_values[tri_i] - fact_values[tri_j]).astype(np.float32)
    injury_diff = np.abs(injury_values[tri_i] - injury_values[tri_j]).astype(np.float32)
    comp_diff = np.abs(comp_values[tri_i] - comp_values[tri_j]).astype(np.float32)

    experiments = build_experiments()
    summary_rows: List[dict] = []
    recommend_rows: List[dict] = []

    for exp in experiments:
        fact_w = np.float32(exp["fact_w"])
        injury_w = np.float32(exp["injury_w"])
        comp_w = np.float32(exp["comp_w"])

        distances = fact_w * fact_diff + injury_w * injury_diff + comp_w * comp_diff

        q05 = quantile_value(distances, 0.05)
        q10 = quantile_value(distances, 0.10)
        q20 = quantile_value(distances, 0.20)
        q30 = quantile_value(distances, 0.30)
        q40 = quantile_value(distances, 0.40)
        q50 = quantile_value(distances, 0.50)

        row = {
            "exp_id": exp["exp_id"],
            "label": exp["label"],
            "fact_w": exp["fact_w"],
            "injury_w": exp["injury_w"],
            "comp_w": exp["comp_w"],
            "pair_count": int(distances.size),
            "min_d": float(np.min(distances)),
            "max_d": float(np.max(distances)),
            "mean_d": float(np.mean(distances)),
            "std_d": float(np.std(distances)),
            "q05": q05,
            "q10": q10,
            "q20": q20,
            "q30": q30,
            "q40": q40,
            "q50": q50,
            "ratio_le_0_05": ratio_le(distances, 0.05),
            "ratio_le_0_10": ratio_le(distances, 0.10),
            "ratio_le_0_15": ratio_le(distances, 0.15),
            "ratio_le_0_20": ratio_le(distances, 0.20),
            "ratio_le_0_25": ratio_le(distances, 0.25),
            "ratio_le_0_30": ratio_le(distances, 0.30),
        }
        summary_rows.append(row)

        recommend_rows.append({
            "exp_id": exp["exp_id"],
            "label": exp["label"],
            "recommended_low": round(q10, 4),
            "recommended_mid": round(q20, 4),
            "recommended_high": round(q30, 4),
            "note": "low=q10, mid=q20, high=q30",
        })

    write_csv(
        OUT_SUMMARY_CSV,
        summary_rows,
        [
            "exp_id", "label", "fact_w", "injury_w", "comp_w", "pair_count",
            "min_d", "max_d", "mean_d", "std_d",
            "q05", "q10", "q20", "q30", "q40", "q50",
            "ratio_le_0_05", "ratio_le_0_10", "ratio_le_0_15",
            "ratio_le_0_20", "ratio_le_0_25", "ratio_le_0_30",
        ],
    )
    write_csv(
        OUT_RECOMMEND_CSV,
        recommend_rows,
        ["exp_id", "label", "recommended_low", "recommended_mid", "recommended_high", "note"],
    )
    OUT_SUMMARY_JSON.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_SUMMARY_CSV}")
    print(f"Wrote {OUT_RECOMMEND_CSV}")
    print(f"Wrote {OUT_SUMMARY_JSON}")


if __name__ == "__main__":
    main()
