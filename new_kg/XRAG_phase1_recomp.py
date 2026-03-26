"""
Phase 1 補跑：只重新抽取 Compensation 金額
- LLM 改為抽取實際數字，不再猜等級
- 修正 case 4532 的 litigant 結構錯誤（L0100 → L0110）
- 輸出 phase1_tensors_v3.jsonl
"""

import json, re, time, requests
from pathlib import Path
from chunk_utils import chunk_indictment
import pandas as pd

SRC            = Path(__file__).parent / "phase1_tensors_v2.jsonl"
DST            = Path(__file__).parent / "phase1_tensors_v3.jsonl"
CHECKPOINT     = Path(__file__).parent / "recomp_checkpoint.txt"
EXCEL_PATH     = Path("/home/aru/AI_LAW/6057起訴書_全.xlsx")
OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "gemma3:27b"

COMP_SCORE = {
    "A": 1.0,    # > 250萬
    "B": 0.75,   # 100~250萬
    "C": 0.5,    # 30~100萬
    "D": 0.25,   # < 30萬
    "N": 0.0,
}

def amount_to_level(n: int) -> str:
    if n > 2_500_000: return "A"
    if n > 1_000_000: return "B"
    if n >   300_000: return "C"
    if n >         0: return "D"
    return "N"

def call_ollama(prompt: str, retries=3) -> str:
    for attempt in range(retries):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            }, timeout=120)
            resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception as e:
            print(f"  [Ollama 錯誤 第{attempt+1}次] {e}")
            time.sleep(5)
    return ""

def extract_json(text: str) -> str:
    if "```" in text:
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)
    start = text.find("{")
    end   = text.rfind("}") + 1
    return text[start:end] if start != -1 else ""

def extract_comp_amounts(comp_text: str, conc_text: str) -> dict:
    """LLM 抽取實際金額數字，不猜等級"""
    combined = (comp_text + "\n" + conc_text)[:2000]
    prompt = f"""你是法律文件分析專家。請閱讀以下起訴書賠償段落。

文本：
{combined}

請抽取：
1. 原告向被告請求的賠償「總金額」（所有原告加總，純數字，單位：元）
2. 是否有強制險或保險公司已賠款需從請求金額中扣除（true/false）

請只回答JSON，不要其他文字：
{{"total_plaintiff_amount": 數字, "has_insuranceuction": true或false}}

注意：total_plaintiff_amount 只填數字不含元字，例如 308450"""

    resp = call_ollama(prompt)
    try:
        data = json.loads(extract_json(resp))
        amt  = int(str(data.get("total_plaintiff_amount", 0)).replace(",", ""))
        ded  = bool(data.get("has_insuranceuction", False))
        return {"amount": amt, "has_deduction": ded}
    except Exception as e:
        print(f"  [Comp 解析失敗] {e} | {resp[:80]}")
        return {"amount": 0, "has_deduction": False}

def rebuild_scores(old_scores: dict, comp_result: dict) -> dict:
    """保留 Fact/Injury 分數，只替換 Comp 相關分數"""
    scores = dict(old_scores)
    amt   = comp_result["amount"]
    level = amount_to_level(amt)

    scores["P_Comp"] = COMP_SCORE[level]
    scores["D_Comp"] = COMP_SCORE[level]       # 被告付的 ≈ 原告請求的
    scores["V_Comp"] = old_scores.get("V_Comp", 0.0)  # 連帶責任維持舊值
    scores["E_Comp"] = -0.2 if comp_result["has_deduction"] else 0.0
    return scores

def rebuild_tensor(litigant: dict, scores: dict) -> list:
    """行優先排列"""
    l, s = litigant, scores
    return [
        l["L1"], l["L2"], l["L3"], l["L4"],
        s["P_Fact"],   s["D_Fact"],   s["V_Fact"],   s["E_Fact"],
        s["P_Injury"], s["D_Injury"], s["V_Injury"], s["E_Injury"],
        s["P_Comp"],   s["D_Comp"],   s["V_Comp"],   s["E_Comp"],
    ]

def load_checkpoint() -> set:
    if CHECKPOINT.exists():
        return set(CHECKPOINT.read_text().strip().split("\n"))
    return set()

def save_checkpoint(cid: str):
    with open(CHECKPOINT, "a") as f:
        f.write(f"{cid}\n")

def main():
    print("=== Phase 1 Comp 重跑 ===")

    # 讀 Excel（只需要文本）
    df = pd.read_excel(EXCEL_PATH)
    excel_map = {str(r["case_id"]): str(r["起訴書"]) for _, r in df.iterrows()}

    # 讀現有資料
    records = {}
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                records[str(rec["case_id"])] = rec

    done = load_checkpoint()
    print(f"已完成：{len(done)} 筆，剩餘：{len(records)-len(done)} 筆")

    with open(DST, "a", encoding="utf-8") as out:
        for cid, rec in records.items():
            if cid in done:
                continue

            print(f"\n[{cid}]", end=" ", flush=True)

            # 修正 case 4532 的 litigant 結構錯誤
            if cid == "4532":
                rec["litigant"]["L3"] = 1  # single_defendant = true
                print("(修正 L0100→L0110)", end=" ")

            # 重新抽取 Comp
            text   = excel_map.get(cid, "")
            chunks = chunk_indictment(text)
            comp_result = extract_comp_amounts(
                chunks["compensation_text"],
                chunks["conclusion_text"]
            )
            print(f"金額={comp_result['amount']:,} 保險扣除={comp_result['has_deduction']}", end=" ")

            # 重建 scores 和 tensor
            new_scores = rebuild_scores(rec["scores"], comp_result)
            new_tensor = rebuild_tensor(rec["litigant"], new_scores)

            rec["scores"]            = new_scores
            rec["tensor"]            = new_tensor
            rec["comp_amount"]       = comp_result["amount"]      # 新增：實際金額
            rec["has_insurance"] = comp_result["has_deduction"]

            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            save_checkpoint(cid)
            print("✓")

    print(f"\n完成！輸出：{DST}")

if __name__ == "__main__":
    main()
