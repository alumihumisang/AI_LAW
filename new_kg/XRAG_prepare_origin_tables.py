from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SUMMARY_CSV = BASE_DIR / "experiment_outputs" / "experiment_summary.csv"
OUTPUT_DIR = BASE_DIR / "experiment_outputs"


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["fact_w"] = float(row["fact_w"])
        row["injury_w"] = float(row["injury_w"])
        row["comp_w"] = float(row["comp_w"])
        row["litigant_w"] = float(row.get("litigant_w", 0.0))
        row["distance_threshold"] = float(row["distance_threshold"])
        row["case_count"] = int(row["case_count"])
        row["cases_with_parent"] = int(row["cases_with_parent"])
        row["cases_without_parent"] = int(row["cases_without_parent"])
        row["parent_links"] = int(row["parent_links"])
        row["hop1_links"] = int(row["hop1_links"])
        row["hop2_links"] = int(row["hop2_links"])
        row["avg_hop1_per_case"] = float(row["avg_hop1_per_case"])
        row["avg_hop2_per_case"] = float(row["avg_hop2_per_case"])
        row["avg_parent_distance"] = float(row["avg_parent_distance"])
        row["avg_hop1_distance"] = float(row["avg_hop1_distance"])
        row["avg_hop2_distance"] = float(row["avg_hop2_distance"])
        row["avg_case_score"] = float(row["avg_case_score"])
        row["parent_coverage_rate"] = float(row["parent_coverage_rate"])
        row["has_outgoing_count"] = int(row["has_outgoing_count"])
        row["has_outgoing_rate"] = float(row["has_outgoing_rate"])
        row["isolated_count"] = int(row["isolated_count"])
        row["isolated_rate"] = float(row["isolated_rate"])
        row["component_count"] = int(row["component_count"])
        row["largest_component"] = int(row["largest_component"])
        row["largest_component_rate"] = float(row["largest_component_rate"])
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def short_setting(row: dict) -> str:
    return (
        f"α={row['fact_w']:.1f}, β={row['injury_w']:.1f}, "
        f"1-α-β={row['comp_w']:.1f}, τ={row['distance_threshold']:.3f}"
    )


def weight_setting(row: dict) -> str:
    return (
        f"α={row['fact_w']:.1f}, β={row['injury_w']:.1f}, "
        f"1-α-β={row['comp_w']:.1f}"
    )


def threshold_label(row: dict) -> str:
    return f"tau={row['distance_threshold']:.3f}"


def build_long_table(rows: list[dict]) -> list[dict]:
    output: list[dict] = []
    for row in sorted(rows, key=lambda r: (r["fact_w"], r["injury_w"], r["comp_w"], r["distance_threshold"]), reverse=True):
        total_links = row["parent_links"] + row["hop1_links"] + row["hop2_links"]
        output.append({
            "exp_id": row["exp_id"],
            "label": row["label"],
            "short_setting": short_setting(row),
            "weight_setting": weight_setting(row),
            "threshold_label": threshold_label(row),
            "parameter_setting": row["parameter_setting"],
            "fact_w": f"{row['fact_w']:.1f}",
            "injury_w": f"{row['injury_w']:.1f}",
            "comp_w": f"{row['comp_w']:.1f}",
            "litigant_w": f"{row['litigant_w']:.2f}",
            "distance_threshold": f"{row['distance_threshold']:.3f}",
            "case_count": row["case_count"],
            "root_case_id": row["root_case_id"],
            "root_score": f"{float(row['root_score']):.6f}",
            "parent_coverage_rate": f"{row['parent_coverage_rate']:.6f}",
            "avg_hop1_per_case": f"{row['avg_hop1_per_case']:.6f}",
            "avg_hop2_per_case": f"{row['avg_hop2_per_case']:.6f}",
            "avg_total_links_per_case": f"{(total_links / row['case_count']):.6f}",
            "has_outgoing_count": row["has_outgoing_count"],
            "has_outgoing_rate": f"{row['has_outgoing_rate']:.6f}",
            "isolated_count": row["isolated_count"],
            "isolated_rate": f"{row['isolated_rate']:.6f}",
            "component_count": row["component_count"],
            "largest_component": row["largest_component"],
            "largest_component_rate": f"{row['largest_component_rate']:.6f}",
            "parent_links": row["parent_links"],
            "hop1_links": row["hop1_links"],
            "hop2_links": row["hop2_links"],
            "avg_parent_distance": f"{row['avg_parent_distance']:.6f}",
            "avg_hop1_distance": f"{row['avg_hop1_distance']:.6f}",
            "avg_hop2_distance": f"{row['avg_hop2_distance']:.6f}",
            "avg_case_score": f"{row['avg_case_score']:.6f}",
        })
    return output


def build_heatmap_table(rows: list[dict], metric_key: str, metric_name: str) -> list[dict]:
    by_weight: dict[str, dict[float, str]] = {}
    for row in rows:
        wkey = weight_setting(row)
        by_weight.setdefault(wkey, {})
        by_weight[wkey][row["distance_threshold"]] = f"{row[metric_key]:.6f}"

    output: list[dict] = []
    for wkey in sorted(by_weight.keys(), reverse=True):
        output.append({
            "weight_setting": wkey,
            "tau_0.075": by_weight[wkey].get(0.075, ""),
            "tau_0.100": by_weight[wkey].get(0.1, ""),
            "tau_0.125": by_weight[wkey].get(0.125, ""),
            "metric": metric_name,
        })
    return output


def main() -> None:
    rows = load_rows(SUMMARY_CSV)
    long_rows = build_long_table(rows)
    write_csv(
        OUTPUT_DIR / "origin_plot_long.csv",
        long_rows,
        [
            "exp_id",
            "label",
            "short_setting",
            "weight_setting",
            "threshold_label",
            "parameter_setting",
            "fact_w",
            "injury_w",
            "comp_w",
            "litigant_w",
            "distance_threshold",
            "case_count",
            "root_case_id",
            "root_score",
            "parent_coverage_rate",
            "avg_hop1_per_case",
            "avg_hop2_per_case",
            "avg_total_links_per_case",
            "has_outgoing_count",
            "has_outgoing_rate",
            "isolated_count",
            "isolated_rate",
            "component_count",
            "largest_component",
            "largest_component_rate",
            "parent_links",
            "hop1_links",
            "hop2_links",
            "avg_parent_distance",
            "avg_hop1_distance",
            "avg_hop2_distance",
            "avg_case_score",
        ],
    )

    write_csv(
        OUTPUT_DIR / "origin_heatmap_parent_coverage.csv",
        build_heatmap_table(rows, "parent_coverage_rate", "parent_coverage_rate"),
        ["weight_setting", "tau_0.075", "tau_0.100", "tau_0.125", "metric"],
    )

    write_csv(
        OUTPUT_DIR / "origin_heatmap_hop1.csv",
        build_heatmap_table(rows, "avg_hop1_per_case", "avg_hop1_per_case"),
        ["weight_setting", "tau_0.075", "tau_0.100", "tau_0.125", "metric"],
    )

    write_csv(
        OUTPUT_DIR / "origin_heatmap_hop2.csv",
        build_heatmap_table(rows, "avg_hop2_per_case", "avg_hop2_per_case"),
        ["weight_setting", "tau_0.075", "tau_0.100", "tau_0.125", "metric"],
        )


if __name__ == "__main__":
    main()
