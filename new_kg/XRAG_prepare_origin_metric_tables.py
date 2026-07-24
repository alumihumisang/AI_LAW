from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SUMMARY_CSV = BASE_DIR / "evaluation_outputs" / "eval_0519_topk3_full_summary.csv"
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

METRICS = [
    ("bleu", "BLEU"),
    ("rouge_l", "ROUGE-L"),
    ("bertscore", "BERTScore"),
]


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ordered_rows(summary_rows: list[dict]) -> list[dict]:
    by_label = {row["system_label"]: row for row in summary_rows}
    ordered = []
    for idx, label in enumerate(SYSTEM_ORDER, start=1):
        row = by_label.get(label)
        if not row:
            continue
        ordered.append({
            "plot_order": idx,
            "system_label": label,
            "family": row["family"],
            "top_k": row["top_k"],
            "num_queries": row["num_queries"],
            "bleu": row["bleu"],
            "rouge_l": row["rouge_l"],
            "bertscore": row["bertscore"],
        })
    return ordered


def build_metric_rows(rows: list[dict], metric_key: str, metric_label: str) -> list[dict]:
    output = []
    for row in rows:
        output.append({
            "plot_order": row["plot_order"],
            "system_label": row["system_label"],
            "family": row["family"],
            "metric": metric_label,
            "value": row[metric_key],
        })
    return output


def build_wide_metric_row(rows: list[dict], metric_key: str) -> list[dict]:
    wide = {"metric": metric_key}
    for row in rows:
        wide[row["system_label"]] = row[metric_key]
    return [wide]


def main() -> None:
    summary_rows = load_rows(SUMMARY_CSV)
    rows = ordered_rows(summary_rows)

    write_csv(
        OUTPUT_DIR / "origin_metrics_all.csv",
        rows,
        ["plot_order", "system_label", "family", "top_k", "num_queries", "bleu", "rouge_l", "bertscore"],
    )

    for metric_key, metric_label in METRICS:
        write_csv(
            OUTPUT_DIR / f"origin_{metric_key}_long.csv",
            build_metric_rows(rows, metric_key, metric_label),
            ["plot_order", "system_label", "family", "metric", "value"],
        )
        write_csv(
            OUTPUT_DIR / f"origin_{metric_key}_wide.csv",
            build_wide_metric_row(rows, metric_key),
            ["metric"] + [row["system_label"] for row in rows],
        )

    print(f"saved={OUTPUT_DIR / 'origin_metrics_all.csv'}")
    for metric_key, _ in METRICS:
        print(f"saved={OUTPUT_DIR / f'origin_{metric_key}_long.csv'}")
        print(f"saved={OUTPUT_DIR / f'origin_{metric_key}_wide.csv'}")


if __name__ == "__main__":
    main()
