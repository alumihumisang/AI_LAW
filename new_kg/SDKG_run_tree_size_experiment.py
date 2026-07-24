from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import XRAG_query_generate as qg
from SDKG_run_50q_18exp_topk1to8 import (
    load_existing_records,
    make_error_record,
    parse_exp_names,
    rewrite_jsonl,
    select_queries,
    sorted_records,
)


BASE_DIR = Path(__file__).resolve().parent
GENERATION_DIR = BASE_DIR / "generation_outputs"
EVALUATION_DIR = BASE_DIR / "evaluation_outputs"
TREE_DIR = BASE_DIR / "experiment_outputs" / "severity_trees"
DEFAULT_CASE_COUNTS = [1000, 2000, 3000, 4000, 5000, 6057]


def parse_int_list(value: str) -> list[int]:
    result: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if part:
            result.append(int(part))
    return result


def output_paths(output_prefix: str, exp_name: str, case_count: int) -> tuple[Path, Path]:
    GENERATION_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{output_prefix}_n{case_count}_{exp_name}"
    return GENERATION_DIR / f"{stem}.jsonl", GENERATION_DIR / f"{stem}.csv"


def tree_links_path(case_count: int, lambda_legal: float) -> Path:
    suffix = f"lambda_{lambda_legal:.2f}".replace(".", "p")
    suffix += f"_n{case_count}"
    return TREE_DIR / f"severity_tree_parent_links_{suffix}.csv"


def build_tree_links(case_count: int, lambda_legal: float, chunk_size: int) -> Path:
    links_path = tree_links_path(case_count, lambda_legal)
    if links_path.exists() and links_path.stat().st_size > 0:
        print(f"[tree n={case_count}] reuse {links_path}", flush=True)
        return links_path

    cmd = [
        sys.executable,
        str(BASE_DIR / "XRAG_phase2_build_severity_trees.py"),
        "--max-cases",
        str(case_count),
        "--lambda-legal",
        str(lambda_legal),
        "--chunk-size",
        str(chunk_size),
        "--output-dir",
        str(TREE_DIR),
    ]
    print(f"[tree n={case_count}] build links lambda={lambda_legal}", flush=True)
    subprocess.run(cmd, check=True)
    return links_path


def add_case_count_to_record(record: dict, case_count: int, lambda_legal: float) -> dict:
    record["case_count"] = case_count
    record["lambda_legal"] = lambda_legal
    record["lambda_severity"] = 1.0 - lambda_legal
    return record


def run_generation_for_case_count(
    case_count: int,
    exp: dict,
    top_k: int,
    model: str,
    query_ids: str,
    output_prefix: str,
    lambda_legal: float,
    links_path: Path,
) -> Path:
    qg.SEVERITY_TREE_LINKS_FILE = links_path
    qg.EXPERIMENT_TREE_CACHE.clear()

    jsonl_path, csv_path = output_paths(output_prefix, exp["short_name"], case_count)
    records_by_key = load_existing_records(jsonl_path)
    rewrite_jsonl(jsonl_path, sorted_records(records_by_key))
    qg.rewrite_progress_csv(csv_path, sorted_records(records_by_key))

    target_queries = select_queries(query_ids)
    corpus_rows, litigant_values, fact_values, injury_values, comp_values, case_sort = qg.load_case_corpus(case_count)
    corpus_by_id = {str(rec["case_id"]): rec for rec in corpus_rows}
    case_idx_by_id = {str(rec["case_id"]): idx for idx, rec in enumerate(corpus_rows)}

    expected = len(target_queries)
    existing_ok = sum(1 for rec in records_by_key.values() if rec.get("run_status") == "ok")
    print(
        f"[generation n={case_count}] exp={exp['short_name']} top_k={top_k} "
        f"existing_ok={existing_ok}/{expected} output={jsonl_path.name}",
        flush=True,
    )

    for idx, query_row in enumerate(target_queries, start=1):
        key = (int(query_row["query_id"]), int(top_k))
        existing = records_by_key.get(key)
        if existing and existing.get("run_status") == "ok":
            print(f"[generation n={case_count} {idx}/{expected}] skip query_id={query_row['query_id']}", flush=True)
            continue

        print(f"[generation n={case_count} {idx}/{expected}] running query_id={query_row['query_id']}", flush=True)
        try:
            record = qg.run_generation_for_query(
                query_row,
                exp,
                corpus_rows,
                litigant_values,
                fact_values,
                injury_values,
                comp_values,
                case_sort,
                corpus_by_id,
                case_idx_by_id,
                top_k,
                model,
            )
            record["run_status"] = "ok"
            record["error_message"] = ""
        except Exception as exc:
            record = make_error_record(query_row, exp, top_k, model, exc)
            print(f"[generation n={case_count} {idx}/{expected}] failed query_id={query_row['query_id']} error={exc}", flush=True)

        records_by_key[key] = add_case_count_to_record(record, case_count, lambda_legal)
        current_records = sorted_records(records_by_key)
        rewrite_jsonl(jsonl_path, current_records)
        qg.rewrite_progress_csv(csv_path, current_records)

    return jsonl_path


def evaluate_one_size(jsonl_path: Path, output_stem: str) -> Path:
    cmd = [
        sys.executable,
        str(BASE_DIR / "XRAG_evaluate_generation.py"),
        "--xrag-jsonl",
        str(jsonl_path),
        "--output-dir",
        str(EVALUATION_DIR),
        "--output-stem",
        output_stem,
    ]
    print(f"[evaluate] {jsonl_path.name}", flush=True)
    subprocess.run(cmd, check=True)
    return EVALUATION_DIR / f"{output_stem}_summary.csv"


def read_summary_row(summary_path: Path, case_count: int, lambda_legal: float) -> dict:
    with summary_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    dkg_rows = [row for row in rows if row.get("family") == "DKG"]
    if not dkg_rows:
        raise ValueError(f"No DKG summary row found in {summary_path}")
    row = dkg_rows[0]
    return {
        "case_count": case_count,
        "system_label": row.get("system_label", ""),
        "top_k": row.get("top_k", ""),
        "lambda_legal": lambda_legal,
        "lambda_severity": 1.0 - lambda_legal,
        "num_queries": row.get("num_queries", ""),
        "bertscore": row.get("bertscore", ""),
        "bleu": row.get("bleu", ""),
        "rouge_l": row.get("rouge_l", ""),
        "human_score": row.get("human_score", ""),
    }


def write_combined_summary(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_count",
        "system_label",
        "top_k",
        "lambda_legal",
        "lambda_severity",
        "num_queries",
        "bertscore",
        "bleu",
        "rouge_l",
        "human_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SDKG tree-size experiment for fixed top-k and fixed parameter setting.")
    parser.add_argument("--case-counts", default=",".join(str(n) for n in DEFAULT_CASE_COUNTS))
    parser.add_argument("--exp-name", default="FC-H")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--lambda-legal", type=float, default=0.5)
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--model", default=qg.DEFAULT_MODEL)
    parser.add_argument("--query-ids", default="")
    parser.add_argument("--output-prefix", default="SDKG_tree_size_topk8")
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-evaluation", action="store_true")
    args = parser.parse_args()

    case_counts = parse_int_list(args.case_counts)
    if not case_counts:
        raise ValueError("--case-counts cannot be empty")

    target_experiments = qg.select_target_experiments(None)
    requested_exp_names = set(parse_exp_names(args.exp_name))
    target_experiments = [exp for exp in target_experiments if exp["short_name"] in requested_exp_names]
    if len(target_experiments) != 1:
        raise ValueError(f"Expected exactly one experiment for --exp-name={args.exp_name}, got {len(target_experiments)}")
    exp = target_experiments[0]

    combined_rows: list[dict] = []
    for case_count in case_counts:
        links_path = build_tree_links(case_count, args.lambda_legal, args.chunk_size)
        jsonl_path, _ = output_paths(args.output_prefix, exp["short_name"], case_count)
        if not args.skip_generation:
            jsonl_path = run_generation_for_case_count(
                case_count,
                exp,
                args.top_k,
                args.model,
                args.query_ids,
                args.output_prefix,
                args.lambda_legal,
                links_path,
            )
        if not args.skip_evaluation:
            eval_stem = f"{args.output_prefix}_n{case_count}_{exp['short_name']}_eval"
            summary_path = evaluate_one_size(jsonl_path, eval_stem)
            combined_rows.append(read_summary_row(summary_path, case_count, args.lambda_legal))

    if combined_rows:
        combined_path = EVALUATION_DIR / f"{args.output_prefix}_{exp['short_name']}_summary_by_case_count.csv"
        write_combined_summary(combined_path, combined_rows)
        print(f"[done] combined_summary={combined_path}", flush=True)


if __name__ == "__main__":
    main()
