from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SUMMARY_CSV = BASE_DIR / "evaluation_outputs" / "eval_smoke5_topk1to8_summary.csv"
OUTPUT_DIR = BASE_DIR / "evaluation_outputs"

SYSTEM_ORDER = [
    "FI-L", "FI-M", "FI-H",
    "FC-L", "FC-M", "FC-H",
    "IF-L", "IF-M", "IF-H",
    "CF-L", "CF-M", "CF-H",
    "IC-L", "IC-M", "IC-H",
    "CI-L", "CI-M", "CI-H",
    "TAARN", "gpt-4o-mini",
]
TOP_K_ORDER = [1, 2, 3, 4, 5, 6, 7, 8]
METRICS = [
    ("bleu", "BLEU"),
    ("rouge_l", "ROUGE-L"),
    ("bertscore", "BERTScore"),
]


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ordered_rows(summary_rows: list[dict]) -> list[dict]:
    by_key = {(row["system_label"], int(row["top_k"])): row for row in summary_rows}
    output: list[dict] = []
    for system_order, system_label in enumerate(SYSTEM_ORDER, start=1):
        for top_k in TOP_K_ORDER:
            row = by_key.get((system_label, top_k))
            if not row:
                continue
            output.append({
                "system_order": system_order,
                "system_label": system_label,
                "family": row["family"],
                "top_k": top_k,
                "num_queries": row["num_queries"],
                "bleu": row["bleu"],
                "rouge_l": row["rouge_l"],
                "bertscore": row["bertscore"],
            })
    return output


def build_metric_long(rows: list[dict], metric_key: str, metric_label: str) -> list[dict]:
    return [
        {
            "system_order": row["system_order"],
            "system_label": row["system_label"],
            "family": row["family"],
            "top_k": row["top_k"],
            "metric": metric_label,
            "value": row[metric_key],
        }
        for row in rows
    ]


def build_metric_wide(rows: list[dict], metric_key: str) -> list[dict]:
    by_system: dict[str, dict[int, str]] = {}
    family_by_system: dict[str, str] = {}
    for row in rows:
        by_system.setdefault(row["system_label"], {})
        by_system[row["system_label"]][row["top_k"]] = row[metric_key]
        family_by_system[row["system_label"]] = row["family"]

    output: list[dict] = []
    for system_order, system_label in enumerate(SYSTEM_ORDER, start=1):
        if system_label not in by_system:
            continue
        wide_row = {
            "system_order": system_order,
            "system_label": system_label,
            "family": family_by_system[system_label],
        }
        for top_k in TOP_K_ORDER:
            wide_row[f"k_{top_k}"] = by_system[system_label].get(top_k, "")
        output.append(wide_row)
    return output


def build_metric_originpro(rows: list[dict], metric_key: str, x_label: str = "top_k") -> list[dict]:
    by_system: dict[str, dict[int, str]] = {}
    for row in rows:
        by_system.setdefault(row["system_label"], {})
        by_system[row["system_label"]][row["top_k"]] = row[metric_key]

    output: list[dict] = []
    for top_k in TOP_K_ORDER:
        origin_row = {x_label: top_k}
        for system_label in SYSTEM_ORDER:
            if system_label not in by_system:
                continue
            origin_row[system_label] = by_system[system_label].get(top_k, "")
        output.append(origin_row)
    return output


def main() -> None:
    summary_rows = load_rows(SUMMARY_CSV)
    rows = ordered_rows(summary_rows)

    write_csv(
        OUTPUT_DIR / "origin_topk_metrics_all.csv",
        rows,
        ["system_order", "system_label", "family", "top_k", "num_queries", "bleu", "rouge_l", "bertscore"],
    )

    for metric_key, metric_label in METRICS:
        write_csv(
            OUTPUT_DIR / f"origin_topk_{metric_key}_long.csv",
            build_metric_long(rows, metric_key, metric_label),
            ["system_order", "system_label", "family", "top_k", "metric", "value"],
        )
        write_csv(
            OUTPUT_DIR / f"origin_topk_{metric_key}_wide.csv",
            build_metric_wide(rows, metric_key),
            ["system_order", "system_label", "family"] + [f"k_{top_k}" for top_k in TOP_K_ORDER],
        )
        write_csv(
            OUTPUT_DIR / f"origin_topk_{metric_key}_originpro.csv",
            build_metric_originpro(rows, metric_key),
            ["top_k"] + [system_label for system_label in SYSTEM_ORDER if system_label in {row['system_label'] for row in rows}],
        )

    print(f"saved={OUTPUT_DIR / 'origin_topk_metrics_all.csv'}")
    for metric_key, _ in METRICS:
        print(f"saved={OUTPUT_DIR / f'origin_topk_{metric_key}_long.csv'}")
        print(f"saved={OUTPUT_DIR / f'origin_topk_{metric_key}_wide.csv'}")
        print(f"saved={OUTPUT_DIR / f'origin_topk_{metric_key}_originpro.csv'}")


if __name__ == "__main__":
    main()
