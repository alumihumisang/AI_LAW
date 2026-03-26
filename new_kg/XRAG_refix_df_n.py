"""
針對 D_Fact=N 的 21 筆，用更新後的 Fact prompt 重新抽取 Fact/Injury
其餘欄位（Litigant、Comp）保留不動
輸出：phase1_tensors_v3.jsonl 原地更新（先寫 v4 再取代）
"""
import json, time, requests
from pathlib import Path
from chunk_utils import chunk_indictment
import pandas as pd

SRC        = Path(__file__).parent / "phase1_tensors_v3.jsonl"
DST        = Path(__file__).parent / "phase1_tensors_v4.jsonl"
EXCEL_PATH = Path("/home/aru/AI_LAW/6057起訴書_全.xlsx")
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"

FACT_SCORE = {"A":1.0,"B":0.8,"C":0.6,"D":0.4,"E":0.2,"N":0.0}
INJURY_SCORE = {"A":1.0,"B":0.8,"C":0.6,"D":0.4,"E":0.2,"N":0.0}

TARGET_IDS = {
    "79","275","491","539","757","1273","2045","2310","2552",
    "2689","3258","3283","3293","3296","3330","4115","4632",
    "5367","5368","5394","5415"
}

def call_ollama(prompt, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL, "prompt": prompt,
                "stream": False, "options": {"temperature": 0.0}
            }, timeout=120)
            resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception as e:
            print(f"  [Ollama 錯誤 第{attempt+1}次] {e}")
            time.sleep(5)
    return ""

def extract_json(text):
    if "```" in text:
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)
    s, e = text.find("{"), text.rfind("}") + 1
    return text[s:e] if s != -1 else ""

def resolve_cat(raw):
    for ch in str(raw).upper():
        if ch in "ABCDEN":
            return ch
    return "N"

def extract_fact_injury(fact_text):
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
    except:
        return {r: {"Fact":"N","Injury":"N"} for r in ["Plaintiff","Defendant","Vicarious","External"]}

def rebuild_tensor(litigant, scores):
    l, s = litigant, scores
    return [
        l["L1"],l["L2"],l["L3"],l["L4"],
        s["P_Fact"],  s["D_Fact"],  s["V_Fact"],  s["E_Fact"],
        s["P_Injury"],s["D_Injury"],s["V_Injury"],s["E_Injury"],
        s["P_Comp"],  s["D_Comp"],  s["V_Comp"],  s["E_Comp"],
    ]

def main():
    print("=== 補跑 D_Fact=N 的 21 筆 ===")

    df = pd.read_excel(EXCEL_PATH)
    excel_map = {str(r["case_id"]): str(r["起訴書"]) for _, r in df.iterrows()}

    records = {}
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                records[str(rec["case_id"])] = rec

    updated = 0
    for cid in TARGET_IDS:
        rec = records.get(cid)
        if not rec:
            print(f"  [警告] case_id={cid} 不存在")
            continue

        print(f"\n[{cid}]", end=" ", flush=True)
        text   = excel_map.get(cid, "")
        chunks = chunk_indictment(text)
        fi     = extract_fact_injury(chunks["fact_text"])

        # 更新 scores（只改 Fact/Injury 部分）
        scores = rec["scores"]
        for role, abbr in [("Plaintiff","P"),("Defendant","D"),("Vicarious","V"),("External","E")]:
            entry = fi.get(role, {})
            if isinstance(entry, str):
                fc, ic = resolve_cat(entry), "N"
            else:
                fc = resolve_cat(entry.get("Fact","N"))
                ic = resolve_cat(entry.get("Injury","N"))
            scores[f"{abbr}_Fact"]   = FACT_SCORE[fc]
            scores[f"{abbr}_Injury"] = INJURY_SCORE[ic]

        rec["scores"] = scores
        rec["tensor"] = rebuild_tensor(rec["litigant"], scores)
        records[cid]  = rec

        print(f"D_Fact={fi.get('Defendant',{}).get('Fact','?')} ✓")
        updated += 1

    # 寫出全部 6057 筆（其他筆不動）
    with open(DST, "w", encoding="utf-8") as out:
        for rec in records.values():
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n完成！更新 {updated} 筆 → {DST}")

if __name__ == "__main__":
    main()
