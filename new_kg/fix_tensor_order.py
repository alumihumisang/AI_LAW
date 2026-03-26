"""
把 phase1_tensors.jsonl 的 tensor 改成行優先順序
（先讀 Y1→Y4 每一橫排，每排再 X1→X4）

原本（列優先）：[L1,L2,L3,L4, PF,PI,PC, DF,DI,DC, VF,VI,VC, EF,EI,EC]
修正（行優先）：[L1,L2,L3,L4, PF,DF,VF,EF, PI,DI,VI,EI, PC,DC,VC,EC]
"""
import json
from pathlib import Path

SRC = Path(__file__).parent / "phase1_tensors.jsonl"
DST = Path(__file__).parent / "phase1_tensors_v2.jsonl"

fixed = 0
with open(SRC, encoding="utf-8") as f_in, \
     open(DST, "w", encoding="utf-8") as f_out:
    for line in f_in:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        s   = rec["scores"]
        l   = rec["litigant"]
        rec["tensor"] = [
            l["L1"], l["L2"], l["L3"], l["L4"],          # Y1 Litigant
            s["P_Fact"],  s["D_Fact"],  s["V_Fact"],  s["E_Fact"],   # Y2 Fact
            s["P_Injury"],s["D_Injury"],s["V_Injury"],s["E_Injury"],  # Y3 Injury
            s["P_Comp"],  s["D_Comp"],  s["V_Comp"],  s["E_Comp"],   # Y4 Comp
        ]
        f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fixed += 1

print(f"完成：{fixed} 筆 → {DST}")
