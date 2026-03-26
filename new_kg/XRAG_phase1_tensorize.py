"""
XRAG Phase 1: Offline Legal Feature Tensorization
將 6,057 筆起訴書文本轉化為特徵張量

資料來源：6057起訴書_全.xlsx
流程：
1. 讀 Excel，切成 fact / laws / compensation / conclusion 四段
2. 用 Gemma3:27b 對 fact_text 做 Litigant Config 分類
3. 用 Gemma3:27b 對 fact_text 做 Fact/Injury 分類
4. 用 Gemma3:27b 對 compensation_text 做 Compensation 金額分類
5. 查表轉固定分數 → 組 Tensor → 存 JSONL
"""

import json
import time
import requests
import pandas as pd
from pathlib import Path
from chunk_utils import chunk_indictment

# ── 設定 ──────────────────────────────────────────────
EXCEL_PATH   = Path("/home/aru/AI_LAW/6057起訴書_全.xlsx")
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"

OUTPUT_FILE     = Path(__file__).parent / "phase1_tensors.jsonl"
CHECKPOINT_FILE = Path(__file__).parent / "phase1_checkpoint.txt"

# ── 查表：類別 → 分數 ──────────────────────────────────
FACT_SCORE = {
    "A": 1.0,   # 酒駕、無照
    "B": 0.8,   # 闖紅燈、逆向、超速
    "C": 0.6,   # 未保持安全距離
    "D": 0.4,   # 未注意車前狀況
    "E": 0.2,   # 猝不及防、閃避不及
    "N": 0.0,
}
INJURY_SCORE = {
    "A": 1.0,   # 植物人、截肢
    "B": 0.8,   # 顱內出血、脊椎骨折、需專人看護
    "C": 0.6,   # 骨折、鋼釘固定、住院
    "D": 0.4,   # 挫傷、腦震盪、復健
    "E": 0.2,   # 擦傷、破皮
    "N": 0.0,
}
COMP_SCORE = {
    "A": 1.0,    # > 250萬
    "B": 0.75,   # 100萬 ~ 250萬
    "C": 0.5,    # 30萬 ~ 100萬
    "D": 0.25,   # < 30萬
    "E": -0.2,   # 強制險已賠、已獲賠償（扣除項）
    "N": 0.0,
}

# ── Ollama ────────────────────────────────────────────
def call_ollama(prompt: str, retries: int = 3) -> str:
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

def resolve_cat(raw: str) -> str:
    """C/D 等模糊回答取第一個有效字母"""
    for ch in str(raw).upper():
        if ch in "ABCDEN":
            return ch
    return "N"

# ── Prompt 1：Litigant Configuration ─────────────────
def extract_litigant(fact_text: str) -> dict:
    prompt = f"""你是法律文件分析專家。請閱讀以下起訴書事實段落，判斷訴訟當事人結構。

文本：
{fact_text[:1500]}

請只回答JSON，不要其他文字：
{{"single_plaintiff":true或false,"multiple_plaintiffs":true或false,"single_defendant":true或false,"multiple_defendants":true或false}}

規則：single/multiple_plaintiff 恰好一個為true，single/multiple_defendant 恰好一個為true"""

    resp = call_ollama(prompt)
    try:
        data = json.loads(extract_json(resp))
        return {
            "L1": 1 if data.get("single_plaintiff")    else 0,
            "L2": 1 if data.get("multiple_plaintiffs") else 0,
            "L3": 1 if data.get("single_defendant")    else 0,
            "L4": 1 if data.get("multiple_defendants") else 0,
        }
    except Exception as e:
        print(f"  [Litigant 解析失敗] {e} | {resp[:80]}")
        return {"L1": 1, "L2": 0, "L3": 1, "L4": 0}

# ── Prompt 2：Fact + Injury（從事實段讀） ─────────────
def extract_fact_injury(fact_text: str) -> dict:
    prompt = f"""你是法律文件分析專家。請閱讀以下起訴書事實段落，為各角色選擇最符合的等級。

文本：
{fact_text[:2000]}

【Fact（被告侵權行為嚴重程度）等級】
A=酒駕/無照駕駛/故意傷害/故意詐欺/重大不法（有意識的嚴重侵害）
B=闖紅燈/逆向行駛/超速/持械傷人/故意毀損財物/蓄意侵入/故意散布不實言論
C=未保持安全距離/過失傷害/醫療疏失/場所設施設計缺陷/外遇通姦侵害配偶權
D=未注意車前狀況/未讓車/飼主未盡管束動物義務/輪胎維護疏失/一般過失義務違反
E=極輕微疏失（客觀上幾乎無責任）
N=文本中完全無法判斷被告有任何違規或過失行為

【Injury（傷害程度）等級】
A=植物人/截肢  B=顱內出血/脊椎骨折/需專人看護  C=骨折/鋼釘/住院  D=挫傷/腦震盪/復健  E=擦傷/破皮  N=無

請只回答JSON，不要其他文字：
{{"Plaintiff":{{"Fact":"?","Injury":"?"}},"Defendant":{{"Fact":"?","Injury":"?"}},"Vicarious":{{"Fact":"?","Injury":"?"}},"External":{{"Fact":"?","Injury":"?"}}}}"""

    resp = call_ollama(prompt)
    try:
        return json.loads(extract_json(resp))
    except Exception as e:
        print(f"  [Fact/Injury 解析失敗] {e} | {resp[:80]}")
        return {r: {"Fact": "N", "Injury": "N"} for r in ["Plaintiff","Defendant","Vicarious","External"]}

# ── Prompt 3：Compensation（從賠償段讀） ──────────────
def extract_compensation(comp_text: str, conc_text: str) -> dict:
    combined = (comp_text + "\n" + conc_text)[:2000]
    prompt = f"""你是法律文件分析專家。請閱讀以下賠償段落，判斷各角色的賠償金額等級。

文本：
{combined}

【Compensation（賠償金額）等級】
A=>250萬  B=100~250萬  C=30~100萬  D=<30萬  E=強制險已賠/已獲賠償（扣除項）  N=無請求

請只回答JSON，不要其他文字：
{{"Plaintiff":{{"Compensation":"?"}},"Defendant":{{"Compensation":"?"}},"Vicarious":{{"Compensation":"?"}},"External":{{"Compensation":"?"}}}}"""

    resp = call_ollama(prompt)
    try:
        return json.loads(extract_json(resp))
    except Exception as e:
        print(f"  [Comp 解析失敗] {e} | {resp[:80]}")
        return {r: {"Compensation": "N"} for r in ["Plaintiff","Defendant","Vicarious","External"]}

# ── 合併 matrix + 查表 ────────────────────────────────
def build_scores(fact_injury: dict, comp: dict) -> dict:
    scores = {}
    for role, abbr in [("Plaintiff","P"),("Defendant","D"),("Vicarious","V"),("External","E")]:
        fi = fact_injury.get(role, {})
        co = comp.get(role, {})
        # LLM 有時回傳 {"Plaintiff": "N"} 而非 {"Plaintiff": {"Fact": "N", ...}}
        if isinstance(fi, str):
            fact_cat = resolve_cat(fi)
            inj_cat  = "N"
        else:
            fact_cat = resolve_cat(fi.get("Fact",   "N"))
            inj_cat  = resolve_cat(fi.get("Injury", "N"))
        if isinstance(co, str):
            comp_cat = resolve_cat(co)
        else:
            comp_cat = resolve_cat(co.get("Compensation", "N"))
        scores[f"{abbr}_Fact"]   = FACT_SCORE  .get(fact_cat, 0.0)
        scores[f"{abbr}_Injury"] = INJURY_SCORE.get(inj_cat,  0.0)
        scores[f"{abbr}_Comp"]   = COMP_SCORE  .get(comp_cat, 0.0)
    return scores

def build_tensor(litigant: dict, scores: dict) -> list:
    return [
        litigant["L1"], litigant["L2"], litigant["L3"], litigant["L4"],
        scores["P_Fact"], scores["P_Injury"], scores["P_Comp"],
        scores["D_Fact"], scores["D_Injury"], scores["D_Comp"],
        scores["V_Fact"], scores["V_Injury"], scores["V_Comp"],
        scores["E_Fact"], scores["E_Injury"], scores["E_Comp"],
    ]

# ── Checkpoint ────────────────────────────────────────
def load_checkpoint() -> set:
    if CHECKPOINT_FILE.exists():
        lines = CHECKPOINT_FILE.read_text().strip().split("\n")
        return set(l for l in lines if l)
    return set()

def save_checkpoint(case_id: str):
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(f"{case_id}\n")

# ── 主程式 ────────────────────────────────────────────
def main():
    print("=== XRAG Phase 1: Feature Tensorization ===")

    done_ids = load_checkpoint()
    print(f"已完成: {len(done_ids)} 筆")

    df = pd.read_excel(EXCEL_PATH)
    print(f"讀取 Excel：{len(df)} 筆")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
        for i, row in df.iterrows():
            cid  = str(row["case_id"])
            text = row["起訴書"] or ""

            if cid in done_ids:
                continue

            print(f"\n[{i+1}/{len(df)}] case_id={cid}")

            # 切段
            chunks = chunk_indictment(text)

            # 三次 LLM 呼叫
            litigant   = extract_litigant(chunks["fact_text"])
            fact_injury = extract_fact_injury(chunks["fact_text"])
            comp        = extract_compensation(chunks["compensation_text"], chunks["conclusion_text"])

            print(f"  Litigant:    {litigant}")
            print(f"  Fact/Injury: { {r: fact_injury[r] for r in ['Plaintiff','Defendant']} }")
            print(f"  Comp:        { {r: comp[r] for r in ['Plaintiff','Defendant']} }")

            scores = build_scores(fact_injury, comp)
            tensor = build_tensor(litigant, scores)
            print(f"  Tensor: {tensor}")

            record = {
                "case_id":           cid,
                "litigant":          litigant,
                "fact_injury_matrix": fact_injury,
                "comp_matrix":       comp,
                "scores":            scores,
                "tensor":            tensor,
                # 切段文本存起來供 Phase 2 寫入 KG
                "fact_text":         chunks["fact_text"],
                "laws_text":         chunks["laws_text"],
                "compensation_text": chunks["compensation_text"],
                "conclusion_text":   chunks["conclusion_text"],
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            save_checkpoint(cid)

    print(f"\n=== 完成！輸出：{OUTPUT_FILE} ===")

if __name__ == "__main__":
    main()
