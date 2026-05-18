"""
XRAG Phase 2: 18-experiment local case graph construction

Purpose:
- Keep the 6057 Case nodes fixed
- Sweep 18 experiment settings:
    6 weight permutations over Fact / Injury / Compensation
    3 distance thresholds
- Compute experiment-specific Score_i and d(i,j)
- Build visible Neo4j links for:
    parent case
    1-hop children
    2-hop cases
- Export summary CSV files for later Origin plotting

Important:
- No "routing" terminology is used here
- One shared Case node set is reused across all experiments
- Experiment variants are distinguished by Experiment nodes and
  relationship properties
- For Neo4j demo display, each experiment node also receives a
  dedicated label such as :E01, :E02, etc.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict, deque
from itertools import permutations
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np
from neo4j import GraphDatabase


BASE_DIR = Path(__file__).resolve().parent
SEVERITY_FILE = BASE_DIR / "phase1_boolean_severity_v1.jsonl"
ENV_FILE = BASE_DIR / ".env"
OUTPUT_DIR = BASE_DIR / "experiment_outputs"

WEIGHT_PERMUTATIONS = sorted(set(permutations((0.5, 0.3, 0.2), 3)), reverse=True)
DISTANCE_THRESHOLDS = [0.050, 0.0625, 0.075, 0.0875, 0.100, 0.1125, 0.125, 0.1375, 0.150]

BATCH_SIZE = 500
LITIGANT_DISTANCE_WEIGHT = 0.1


def exp_label(exp_id: str) -> str:
    if not exp_id.startswith("E") or not exp_id[1:].isdigit():
        raise ValueError(f"Unexpected experiment id: {exp_id}")
    return exp_id


def load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def get_config() -> Dict[str, str]:
    file_env = load_env_file(ENV_FILE)
    keys = ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE"]
    cfg = {}
    for key in keys:
        cfg[key] = os.environ.get(key) or file_env.get(key, "")
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Neo4j config: {', '.join(missing)}")
    return cfg


def iter_records(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def safe_mean(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def build_case_arrays(max_cases: int | None = None) -> Dict[str, object]:
    case_ids: List[str] = []
    litigant_vectors: List[List[float]] = []
    fact_values: List[float] = []
    injury_values: List[float] = []
    comp_values: List[float] = []

    for idx, rec in enumerate(iter_records(SEVERITY_FILE)):
        if max_cases is not None and idx >= max_cases:
            break

        scores = rec.get("severity_scores", {})
        litigants = rec.get("boolean_matrix", {}).get("litigants", {})

        case_ids.append(str(rec["case_id"]))
        litigant_vectors.append([
            float(litigants.get("single_plaintiff", 0)),
            float(litigants.get("multiple_plaintiffs", 0)),
            float(litigants.get("single_defendant", 0)),
            float(litigants.get("multiple_defendants", 0)),
        ])
        fact_values.append(float(scores.get("Fact", 0.0)))
        injury_values.append(float(scores.get("Injury", 0.0)))
        comp_values.append(float(scores.get("Compensation", 0.0)))

    case_sort = np.array([int(cid) if cid.isdigit() else 10**12 + i for i, cid in enumerate(case_ids)], dtype=np.int64)

    return {
        "case_ids": case_ids,
        "case_sort": case_sort,
        "litigant_values": np.array(litigant_vectors, dtype=np.float32),
        "fact_values": np.array(fact_values, dtype=np.float32),
        "injury_values": np.array(injury_values, dtype=np.float32),
        "comp_values": np.array(comp_values, dtype=np.float32),
    }


def build_experiments() -> List[dict]:
    experiments: List[dict] = []
    exp_num = 1
    for fact_w, injury_w, comp_w in WEIGHT_PERMUTATIONS:
        for threshold in DISTANCE_THRESHOLDS:
            experiments.append({
                "exp_id": f"E{exp_num:02d}",
                "fact_w": float(fact_w),
                "injury_w": float(injury_w),
                "comp_w": float(comp_w),
                "distance_threshold": float(threshold),
                "label": (
                    f"α={fact_w:.1f}, β={injury_w:.1f}, "
                    f"1-α-β={comp_w:.1f}, τ={threshold:.3f}"
                ),
            })
            exp_num += 1
    return experiments


def choose_order(candidate_idx: np.ndarray, distance_row: np.ndarray, scores: np.ndarray, case_sort: np.ndarray) -> np.ndarray:
    if candidate_idx.size == 0:
        return candidate_idx
    return candidate_idx[
        np.lexsort(
            (
                case_sort[candidate_idx],
                -scores[candidate_idx],
                distance_row[candidate_idx],
            )
        )
    ]


def dedupe_links(link_rows: List[dict]) -> List[dict]:
    priority = {"parent": 0, "hop1": 1, "hop2": 2}
    dedup_by_pair: Dict[tuple[str, str], dict] = {}
    for row in link_rows:
        key = (row["source_case_id"], row["target_case_id"])
        prev = dedup_by_pair.get(key)
        if prev is None:
            dedup_by_pair[key] = row
            continue
        prev_key = (
            priority.get(prev["link_type"], 99),
            int(prev["rank"]),
            float(prev["distance"]),
        )
        new_key = (
            priority.get(row["link_type"], 99),
            int(row["rank"]),
            float(row["distance"]),
        )
        if new_key < prev_key:
            dedup_by_pair[key] = row
    return list(dedup_by_pair.values())


def compute_experiment_graph(
    exp: dict,
    case_ids: List[str],
    case_sort: np.ndarray,
    litigant_values: np.ndarray,
    fact_values: np.ndarray,
    injury_values: np.ndarray,
    comp_values: np.ndarray,
) -> Dict[str, object]:
    fact_w = np.float32(exp["fact_w"])
    injury_w = np.float32(exp["injury_w"])
    comp_w = np.float32(exp["comp_w"])
    threshold = np.float32(exp["distance_threshold"])

    scores = fact_w * fact_values + injury_w * injury_values + comp_w * comp_values
    litigant_distance_matrix = LITIGANT_DISTANCE_WEIGHT * np.abs(
        litigant_values[:, None, :] - litigant_values[None, :, :]
    ).mean(axis=2)

    distance_matrix = (
        fact_w * np.abs(fact_values[:, None] - fact_values[None, :])
        + injury_w * np.abs(injury_values[:, None] - injury_values[None, :])
        + comp_w * np.abs(comp_values[:, None] - comp_values[None, :])
        + litigant_distance_matrix
    ).astype(np.float32)
    np.fill_diagonal(distance_matrix, np.float32(np.inf))

    root_idx = int(np.argmax(scores))
    root_case_id = case_ids[root_idx]

    score_rows: List[dict] = []
    link_rows: List[dict] = []

    parent_distance_values: List[float] = []
    hop1_distance_values: List[float] = []
    hop2_distance_values: List[float] = []
    cases_with_parent = 0
    hop1_edges = 0
    hop2_edges = 0

    for i, cid in enumerate(case_ids):
        score_rows.append({
            "exp_id": exp["exp_id"],
            "case_id": cid,
            "score": float(scores[i]),
            "fact_value": float(fact_values[i]),
            "injury_value": float(injury_values[i]),
            "comp_value": float(comp_values[i]),
        })

        drow = distance_matrix[i]

        if i != root_idx:
            parent_candidates = np.where((scores > scores[i]) & (drow <= threshold))[0]
            parent_candidates = choose_order(parent_candidates, drow, scores, case_sort)
            if parent_candidates.size > 0:
                p = int(parent_candidates[0])
                link_rows.append({
                    "exp_id": exp["exp_id"],
                    "source_case_id": case_ids[p],
                    "target_case_id": cid,
                    "link_type": "parent",
                    "hop": 0,
                    "rank": 1,
                    "distance": float(drow[p]),
                    "source_score": float(scores[p]),
                    "target_score": float(scores[i]),
                })
                parent_distance_values.append(float(drow[p]))
                cases_with_parent += 1

        hop1_candidates = np.where((scores < scores[i]) & (drow <= threshold))[0]
        hop1_candidates = choose_order(hop1_candidates, drow, scores, case_sort)[:3]

        for rank, child_idx in enumerate(hop1_candidates, start=1):
            child = int(child_idx)
            link_rows.append({
                "exp_id": exp["exp_id"],
                "source_case_id": cid,
                "target_case_id": case_ids[child],
                "link_type": "hop1",
                "hop": 1,
                "rank": rank,
                "distance": float(drow[child]),
                "source_score": float(scores[i]),
                "target_score": float(scores[child]),
            })
            hop1_distance_values.append(float(drow[child]))
            hop1_edges += 1

            child_row = distance_matrix[child]
            hop2_candidates = np.where((scores < scores[child]) & (child_row <= threshold))[0]
            hop2_candidates = choose_order(hop2_candidates, child_row, scores, case_sort)[:1]

            for hop2_idx in hop2_candidates:
                gchild = int(hop2_idx)
                link_rows.append({
                    "exp_id": exp["exp_id"],
                    "source_case_id": case_ids[child],
                    "target_case_id": case_ids[gchild],
                    "link_type": "hop2",
                    "hop": 2,
                    "rank": 1,
                    "distance": float(child_row[gchild]),
                    "source_score": float(scores[child]),
                    "target_score": float(scores[gchild]),
                })
                hop2_distance_values.append(float(child_row[gchild]))
                hop2_edges += 1

    link_rows = dedupe_links(link_rows)
    parent_links = sum(1 for row in link_rows if row["link_type"] == "parent")
    hop1_links = sum(1 for row in link_rows if row["link_type"] == "hop1")
    hop2_links = sum(1 for row in link_rows if row["link_type"] == "hop2")

    summary = {
        "exp_id": exp["exp_id"],
        "label": exp["label"],
        "parameter_setting": (
            f"α={exp['fact_w']:.1f}, "
            f"β={exp['injury_w']:.1f}, "
            f"1-α-β={exp['comp_w']:.1f}, "
            f"τ={exp['distance_threshold']:.3f}"
        ),
        "fact_w": exp["fact_w"],
        "injury_w": exp["injury_w"],
        "comp_w": exp["comp_w"],
        "litigant_w": LITIGANT_DISTANCE_WEIGHT,
        "distance_threshold": exp["distance_threshold"],
        "case_count": len(case_ids),
        "root_case_id": root_case_id,
        "root_score": float(scores[root_idx]),
        "cases_with_parent": cases_with_parent,
        "cases_without_parent": len(case_ids) - 1 - cases_with_parent,
        "parent_links": parent_links,
        "hop1_links": hop1_links,
        "hop2_links": hop2_links,
        "avg_hop1_per_case": float(hop1_links) / float(len(case_ids)) if case_ids else 0.0,
        "avg_hop2_per_case": float(hop2_links) / float(len(case_ids)) if case_ids else 0.0,
        "avg_parent_distance": float(np.mean(parent_distance_values)) if parent_distance_values else 0.0,
        "avg_hop1_distance": float(np.mean(hop1_distance_values)) if hop1_distance_values else 0.0,
        "avg_hop2_distance": float(np.mean(hop2_distance_values)) if hop2_distance_values else 0.0,
        "avg_case_score": float(np.mean(scores)) if len(scores) else 0.0,
    }

    incoming_nodes = set()
    outgoing_nodes = set()
    undirected_adj: Dict[str, set[str]] = defaultdict(set)
    for row in link_rows:
        src = row["source_case_id"]
        tgt = row["target_case_id"]
        outgoing_nodes.add(src)
        incoming_nodes.add(tgt)
        undirected_adj[src].add(tgt)
        undirected_adj[tgt].add(src)

    isolated_count = 0
    visited: set[str] = set()
    component_count = 0
    largest_component = 0
    for cid in case_ids:
        if cid not in incoming_nodes and cid not in outgoing_nodes:
            isolated_count += 1
        if cid in visited:
            continue
        component_count += 1
        queue = deque([cid])
        visited.add(cid)
        comp_size = 0
        while queue:
            cur = queue.popleft()
            comp_size += 1
            for nb in undirected_adj.get(cur, ()):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        if comp_size > largest_component:
            largest_component = comp_size

    case_count = len(case_ids)
    summary.update({
        "parent_coverage_rate": float(cases_with_parent) / float(case_count) if case_count else 0.0,
        "has_outgoing_count": len(outgoing_nodes),
        "has_outgoing_rate": float(len(outgoing_nodes)) / float(case_count) if case_count else 0.0,
        "isolated_count": isolated_count,
        "isolated_rate": float(isolated_count) / float(case_count) if case_count else 0.0,
        "component_count": component_count,
        "largest_component": largest_component,
        "largest_component_rate": float(largest_component) / float(case_count) if case_count else 0.0,
    })

    return {
        "experiment": exp,
        "summary": summary,
        "scores": score_rows,
        "links": link_rows,
        "root_case_id": root_case_id,
    }


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_results(results: List[Dict[str, object]]) -> None:
    ensure_output_dir()

    summary_rows = [res["summary"] for res in results]
    score_rows = [row for res in results for row in res["scores"]]
    link_rows = [row for res in results for row in res["links"]]

    write_csv(
        OUTPUT_DIR / "experiment_summary.csv",
        summary_rows,
        [
            "exp_id",
            "label",
            "parameter_setting",
            "fact_w",
            "injury_w",
            "comp_w",
            "litigant_w",
            "distance_threshold",
            "case_count",
            "root_case_id",
            "root_score",
            "cases_with_parent",
            "cases_without_parent",
            "parent_links",
            "hop1_links",
            "hop2_links",
            "avg_hop1_per_case",
            "avg_hop2_per_case",
            "avg_parent_distance",
            "avg_hop1_distance",
            "avg_hop2_distance",
            "avg_case_score",
            "parent_coverage_rate",
            "has_outgoing_count",
            "has_outgoing_rate",
            "isolated_count",
            "isolated_rate",
            "component_count",
            "largest_component",
            "largest_component_rate",
        ],
    )

    write_csv(
        OUTPUT_DIR / "experiment_case_scores.csv",
        score_rows,
        ["exp_id", "case_id", "score", "fact_value", "injury_value", "comp_value"],
    )

    write_csv(
        OUTPUT_DIR / "experiment_links.csv",
        link_rows,
        [
            "exp_id",
            "source_case_id",
            "target_case_id",
            "link_type",
            "hop",
            "rank",
            "distance",
            "source_score",
            "target_score",
        ],
    )


def filter_result_for_demo(res: Dict[str, object], demo_case_ids: set[str]) -> Dict[str, object]:
    if not demo_case_ids:
        return res

    links = res["links"]
    scores = res["scores"]

    selected_links: List[dict] = []
    selected_case_ids: set[str] = set()
    demo_centers: List[str] = []

    for case_id in demo_case_ids:
        parent_links = [
            row for row in links
            if row["link_type"] == "parent" and row["target_case_id"] == case_id
        ]
        hop1_links = [
            row for row in links
            if row["link_type"] == "hop1" and row["source_case_id"] == case_id
        ]
        hop1_children = {row["target_case_id"] for row in hop1_links}
        hop2_links = [
            row for row in links
            if row["link_type"] == "hop2" and row["source_case_id"] in hop1_children
        ]

        for row in parent_links + hop1_links + hop2_links:
            selected_links.append(row)
            selected_case_ids.add(row["source_case_id"])
            selected_case_ids.add(row["target_case_id"])
        selected_case_ids.add(case_id)
        if parent_links or hop1_links or hop2_links:
            demo_centers.append(case_id)

    unique_key = set()
    deduped_links = []
    for row in selected_links:
        key = (
            row["source_case_id"],
            row["target_case_id"],
            row["link_type"],
            row["rank"],
            row["exp_id"],
        )
        if key in unique_key:
            continue
        unique_key.add(key)
        deduped_links.append(row)

    filtered_scores = [row for row in scores if row["case_id"] in selected_case_ids]

    demo_summary = dict(res["summary"])
    demo_summary["demo_case_count"] = len(demo_case_ids)
    demo_summary["demo_node_count"] = len(selected_case_ids)
    demo_summary["demo_link_count"] = len(deduped_links)

    return {
        "experiment": res["experiment"],
        "summary": demo_summary,
        "scores": filtered_scores,
        "links": deduped_links,
        "root_case_id": res["root_case_id"],
        "demo_centers": sorted(set(demo_centers)),
    }


def select_demo_case_ids(res: Dict[str, object], top_k: int) -> List[str]:
    parent_targets = {row["target_case_id"] for row in res["links"] if row["link_type"] == "parent"}
    hop1_counts: Dict[str, int] = {}
    for row in res["links"]:
        if row["link_type"] == "hop1":
            hop1_counts[row["source_case_id"]] = hop1_counts.get(row["source_case_id"], 0) + 1

    candidates = [(cid, cnt) for cid, cnt in hop1_counts.items() if cid in parent_targets]
    candidates.sort(key=lambda x: (-x[1], x[0]))
    return [cid for cid, _ in candidates[:top_k]]


def ensure_neo4j_schema(driver, database: str) -> None:
    statements = [
        "CREATE INDEX case_base_values IF NOT EXISTS FOR (c:Case) ON (c.fact_value_base, c.injury_value_base, c.comp_value_base)",
    ]
    with driver.session(database=database) as session:
        for cypher in statements:
            session.run(cypher)


def wipe_experiment_data(driver, database: str) -> None:
    with driver.session(database=database) as session:
        session.run("MATCH ()-[r:LINKS_TO|DEMO_CENTER|SHOWS_CENTER|ANCHOR_CASE|PARENT_CASE|TOP_PARENT_CASE|PARENT_LINK|PARENT_OF|HOP1_LINK|HOP2_LINK|HAS_SCORE]->() DELETE r")
        session.run("MATCH (d:DemoCase) DETACH DELETE d")
        session.run("MATCH (t:DemoTree) DETACH DELETE t")
        session.run("MATCH (n) WHERE n.exp_id IS NOT NULL AND NOT n:Case DETACH DELETE n")


def sync_case_base_values(
    driver,
    database: str,
    case_ids: List[str],
    fact_values: np.ndarray,
    injury_values: np.ndarray,
    comp_values: np.ndarray,
) -> None:
    rows = [
        {
            "case_id": cid,
            "name": cid,
            "display_name": cid,
            "fact_value_base": float(fact_values[i]),
            "injury_value_base": float(injury_values[i]),
            "comp_value_base": float(comp_values[i]),
        }
        for i, cid in enumerate(case_ids)
    ]

    query = """
    UNWIND $rows AS row
    MATCH (c:Case {case_id: row.case_id})
    SET c.name = row.name,
        c.display_name = row.display_name,
        c.fact_value_base = row.fact_value_base,
        c.injury_value_base = row.injury_value_base,
        c.comp_value_base = row.comp_value_base
    """
    with driver.session(database=database) as session:
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start:start + BATCH_SIZE]
            session.run(query, rows=batch)


def sync_case_display_values(
    driver,
    database: str,
    exp_id: str,
    score_rows: List[dict],
) -> None:
    query = """
    UNWIND $rows AS row
    MATCH (c:Case {case_id: row.case_id})
    SET c.display_exp_id = $exp_id,
        c.display_score = row.score,
        c.display_fact_value = row.fact_value,
        c.display_injury_value = row.injury_value,
        c.display_comp_value = row.comp_value
    """
    with driver.session(database=database) as session:
        for start in range(0, len(score_rows), BATCH_SIZE):
            batch = score_rows[start:start + BATCH_SIZE]
            session.run(query, exp_id=exp_id, rows=batch)


def load_results_to_neo4j(
    driver,
    database: str,
    results: List[Dict[str, object]],
    load_score_rels: bool,
) -> None:
    score_query = """
    UNWIND $rows AS row
    MATCH (e {exp_id: row.exp_id})
    MATCH (c:Case {case_id: row.case_id})
    MERGE (e)-[r:HAS_SCORE]->(c)
    SET r.score = row.score,
        r.fact_value = row.fact_value,
        r.injury_value = row.injury_value,
        r.comp_value = row.comp_value
    """

    parent_query = """
    UNWIND $rows AS row
    MATCH (a:Case {case_id: row.source_case_id})
    MATCH (b:Case {case_id: row.target_case_id})
    MERGE (a)-[r:PARENT_OF {experiment_id: row.exp_id}]->(b)
    SET r.distance = row.distance,
        r.source_score = row.source_score,
        r.target_score = row.target_score
    """

    hop1_query = """
    UNWIND $rows AS row
    MATCH (a:Case {case_id: row.source_case_id})
    MATCH (b:Case {case_id: row.target_case_id})
    MERGE (a)-[r:HOP1_LINK {experiment_id: row.exp_id, rank: row.rank}]->(b)
    SET r.distance = row.distance,
        r.source_score = row.source_score,
        r.target_score = row.target_score
    """

    hop2_query = """
    UNWIND $rows AS row
    MATCH (a:Case {case_id: row.source_case_id})
    MATCH (b:Case {case_id: row.target_case_id})
    MERGE (a)-[r:HOP2_LINK {experiment_id: row.exp_id, rank: row.rank}]->(b)
    SET r.distance = row.distance,
        r.source_score = row.source_score,
        r.target_score = row.target_score
    """

    link_query = """
    UNWIND $rows AS row
    MATCH (a:Case {case_id: row.source_case_id})
    MATCH (b:Case {case_id: row.target_case_id})
    MERGE (a)-[r:LINKS_TO {
      experiment_id: row.exp_id,
      link_type: row.link_type,
      rank: row.rank
    }]->(b)
    SET r.hop = row.hop,
        r.distance = row.distance,
        r.source_score = row.source_score,
        r.target_score = row.target_score
    """

    parent_case_query = """
    UNWIND $rows AS row
    MATCH (e {exp_id: row.exp_id})
    MATCH (c:Case {case_id: row.case_id})
    MERGE (e)-[r:TOP_PARENT_CASE]->(c)
    SET r.rank = row.rank,
        r.score = row.score,
        r.fact_value = row.fact_value,
        r.injury_value = row.injury_value,
        r.comp_value = row.comp_value
    """

    with driver.session(database=database) as session:
        for res in results:
            exp_id = res["experiment"]["exp_id"]
            label = exp_label(exp_id)
            print(f"Loading Neo4j experiment {exp_id} ...")
            experiment_query = f"""
            MERGE (e:`{label}` {{exp_id: $row.exp_id}})
            SET e.name = $row.exp_id,
                e.display_name = $row.exp_id,
                e.label = $row.label,
                e.parameter_setting = $row.parameter_setting,
                e.fact_w = $row.fact_w,
                e.injury_w = $row.injury_w,
                e.comp_w = $row.comp_w,
                e.litigant_w = $row.litigant_w,
                e.distance_threshold = $row.distance_threshold,
                e.root_case_id = $row.root_case_id,
                e.root_score = $row.root_score,
                e.case_count = $row.case_count,
                e.parent_links = $row.parent_links,
                e.hop1_links = $row.hop1_links,
                e.hop2_links = $row.hop2_links,
                e.avg_hop1_per_case = $row.avg_hop1_per_case,
                e.avg_hop2_per_case = $row.avg_hop2_per_case,
                e.parent_coverage_rate = $row.parent_coverage_rate,
                e.has_outgoing_count = $row.has_outgoing_count,
                e.has_outgoing_rate = $row.has_outgoing_rate,
                e.isolated_count = $row.isolated_count,
                e.isolated_rate = $row.isolated_rate,
                e.component_count = $row.component_count,
                e.largest_component = $row.largest_component,
                e.largest_component_rate = $row.largest_component_rate
            """
            session.run(experiment_query, row=res["summary"])
            score_by_case = {row["case_id"]: row["score"] for row in res["scores"]}
            parent_sources = {
                row["source_case_id"] for row in res["links"] if row["link_type"] == "parent"
            }
            parent_targets = {
                row["target_case_id"] for row in res["links"] if row["link_type"] == "parent"
            }
            top_parent_case_ids = sorted(
                parent_sources - parent_targets,
                key=lambda cid: (-score_by_case.get(cid, 0.0), cid),
            )
            if top_parent_case_ids:
                session.run(
                    parent_case_query,
                    rows=[
                        {
                            "exp_id": exp_id,
                            "case_id": cid,
                            "rank": rank,
                            "score": float(score_by_case.get(cid, 0.0)),
                            "fact_value": float(next(row["fact_value"] for row in res["scores"] if row["case_id"] == cid)),
                            "injury_value": float(next(row["injury_value"] for row in res["scores"] if row["case_id"] == cid)),
                            "comp_value": float(next(row["comp_value"] for row in res["scores"] if row["case_id"] == cid)),
                        }
                        for rank, cid in enumerate(top_parent_case_ids, start=1)
                    ],
                )
            shows_center_query = f"""
            MATCH (e:`{label}` {{exp_id: $exp_id}})
            MATCH (c:Case {{case_id: $case_id}})
            MERGE (e)-[:SHOWS_CENTER]->(c)
            """
            for center_case_id in res.get("demo_centers", []):
                session.run(shows_center_query, exp_id=exp_id, case_id=center_case_id)

            scores = res["scores"]
            sync_case_display_values(driver, database, exp_id, scores)
            if load_score_rels:
                for start in range(0, len(scores), BATCH_SIZE):
                    batch = scores[start:start + BATCH_SIZE]
                    session.run(score_query, rows=batch)

            center_set = set(res.get("demo_centers", []))
            if center_set:
                parent_rows = [
                    row for row in res["links"]
                    if row["link_type"] == "parent"
                    and (row["source_case_id"] in center_set or row["target_case_id"] in center_set)
                ]
                for start in range(0, len(parent_rows), BATCH_SIZE):
                    batch = parent_rows[start:start + BATCH_SIZE]
                    session.run(parent_query, rows=batch)
                total_demo_links = len(parent_rows)
            else:
                parent_rows = [row for row in res["links"] if row["link_type"] == "parent"]
                for start in range(0, len(parent_rows), BATCH_SIZE):
                    batch = parent_rows[start:start + BATCH_SIZE]
                    session.run(parent_query, rows=batch)
                total_demo_links = len(parent_rows)
            score_text = f"scores={len(scores)}" if load_score_rels else "scores=skipped"
            print(f"Loaded Neo4j experiment {exp_id}: {score_text}, demo_links={total_demo_links}")


def verify_neo4j_counts(driver, database: str) -> dict:
    with driver.session(database=database) as session:
        experiment_count = session.run("MATCH (e) WHERE e.exp_id IS NOT NULL AND NOT e:Case RETURN count(e) AS c").single()["c"]
        score_rel_count = session.run("MATCH ()-[r:HAS_SCORE]->() RETURN count(r) AS c").single()["c"]
        parent_case_rel_count = session.run("MATCH ()-[r:TOP_PARENT_CASE]->() RETURN count(r) AS c").single()["c"]
        shows_center_rel_count = session.run("MATCH ()-[r:SHOWS_CENTER]->() RETURN count(r) AS c").single()["c"]
        link_rel_count = session.run("MATCH ()-[r:LINKS_TO]->() RETURN count(r) AS c").single()["c"]
        parent_link_count = session.run("MATCH ()-[r:PARENT_OF]->() RETURN count(r) AS c").single()["c"]
        hop1_link_count = session.run("MATCH ()-[r:HOP1_LINK]->() RETURN count(r) AS c").single()["c"]
        hop2_link_count = session.run("MATCH ()-[r:HOP2_LINK]->() RETURN count(r) AS c").single()["c"]
        return {
            "experiment_count": experiment_count,
            "score_rel_count": score_rel_count,
            "parent_case_rel_count": parent_case_rel_count,
            "shows_center_rel_count": shows_center_rel_count,
            "link_rel_count": link_rel_count,
            "parent_link_count": parent_link_count,
            "hop1_link_count": hop1_link_count,
            "hop2_link_count": hop2_link_count,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-neo4j", action="store_true", help="Only compute and export CSV files")
    parser.add_argument("--wipe-experiments", action="store_true", help="Delete existing experiment nodes and experiment links before loading")
    parser.add_argument("--max-cases", type=int, default=None, help="Limit the number of cases for quick testing")
    parser.add_argument("--verify-only", action="store_true", help="Only check current experiment counts in Neo4j")
    parser.add_argument(
        "--neo4j-exp-ids",
        type=str,
        default="",
        help="Comma-separated experiment ids to load into Neo4j, e.g. E01,E02,E03. Leave empty to load all computed experiments.",
    )
    parser.add_argument(
        "--load-score-rels",
        action="store_true",
        help="Also create Experiment-[:HAS_SCORE]->Case relationships in Neo4j. Disabled by default to save Aura relationship quota.",
    )
    parser.add_argument(
        "--demo-case-ids",
        type=str,
        default="",
        help="Comma-separated case ids. If set, only local parent / 1-hop / 2-hop trees for these center cases are loaded into Neo4j.",
    )
    parser.add_argument(
        "--demo-top-k",
        type=int,
        default=0,
        help="Automatically select the top-k center cases per experiment for demo trees.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verify_only:
        cfg = get_config()
        driver = GraphDatabase.driver(
            cfg["NEO4J_URI"],
            auth=(cfg["NEO4J_USERNAME"], cfg["NEO4J_PASSWORD"]),
        )
        counts = verify_neo4j_counts(driver, cfg["NEO4J_DATABASE"])
        driver.close()
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return

    arrays = build_case_arrays(max_cases=args.max_cases)
    case_ids = arrays["case_ids"]
    case_sort = arrays["case_sort"]
    litigant_values = arrays["litigant_values"]
    fact_values = arrays["fact_values"]
    injury_values = arrays["injury_values"]
    comp_values = arrays["comp_values"]

    print(f"Loaded fixed case feature set: {len(case_ids)} cases")

    experiments = build_experiments()
    results: List[Dict[str, object]] = []

    for exp in experiments:
        print(
            f"[{exp['exp_id']}] "
            f"α={exp['fact_w']:.1f} β={exp['injury_w']:.1f} "
            f"1-α-β={exp['comp_w']:.1f} τ={exp['distance_threshold']:.3f}"
        )
        results.append(
            compute_experiment_graph(
                exp=exp,
                case_ids=case_ids,
                case_sort=case_sort,
                litigant_values=litigant_values,
                fact_values=fact_values,
                injury_values=injury_values,
                comp_values=comp_values,
            )
        )

    export_results(results)
    print(f"Wrote CSV outputs to: {OUTPUT_DIR}")

    if args.skip_neo4j:
        print("Skipped Neo4j loading by request.")
        return

    selected_results = results
    if args.neo4j_exp_ids.strip():
        selected_ids = {token.strip() for token in args.neo4j_exp_ids.split(",") if token.strip()}
        selected_results = [res for res in results if res["experiment"]["exp_id"] in selected_ids]
        print(f"Selected Neo4j experiment ids: {', '.join(sorted(selected_ids))}")
        print(f"Experiments to load into Neo4j: {len(selected_results)}")

    demo_case_ids: set[str] = set()
    if args.demo_case_ids.strip():
        demo_case_ids = {token.strip() for token in args.demo_case_ids.split(",") if token.strip()}
        print(f"Demo center cases: {', '.join(sorted(demo_case_ids))}")
        selected_results = [filter_result_for_demo(res, demo_case_ids) for res in selected_results]
    elif args.demo_top_k > 0:
        selected_results = [
            filter_result_for_demo(res, set(select_demo_case_ids(res, args.demo_top_k)))
            for res in selected_results
        ]
        print(f"Demo center selection: top-{args.demo_top_k} per experiment")

    cfg = get_config()
    driver = GraphDatabase.driver(
        cfg["NEO4J_URI"],
        auth=(cfg["NEO4J_USERNAME"], cfg["NEO4J_PASSWORD"]),
    )

    ensure_neo4j_schema(driver, cfg["NEO4J_DATABASE"])
    if args.wipe_experiments:
        print("Deleting existing experiment graph data ...")
        wipe_experiment_data(driver, cfg["NEO4J_DATABASE"])

    sync_case_base_values(
        driver,
        cfg["NEO4J_DATABASE"],
        case_ids=case_ids,
        fact_values=fact_values,
        injury_values=injury_values,
        comp_values=comp_values,
    )
    load_results_to_neo4j(
        driver,
        cfg["NEO4J_DATABASE"],
        selected_results,
        load_score_rels=args.load_score_rels,
    )
    driver.close()
    print("Neo4j experiment graph loading complete.")


if __name__ == "__main__":
    main()
