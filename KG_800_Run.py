#!/usr/bin/env python3
"""
起訴狀生成器 (精簡優化版本)
"""

import os
import re
import pandas as pd
import warnings
from typing import List, Dict, Any
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from Elasticsearch_utils import ElasticsearchManager
from KG_6_Vectorize_And_Store_ES import KGVectorizer
from Neo4j_manager_utils import Neo4jManager
from text_processor import TextProcessor  # 若有其他需求，此處可以留空或自訂

# --------------------
# 輔助函式：數字格式轉換
# --------------------
def fullwidth_to_halfwidth(s: str) -> str:
    """將全形數字轉換為半形"""
    return ''.join(chr(ord(char) - 0xFEE0) if '０' <= char <= '９' else char for char in s)

def chinese_to_arabic(cn: str) -> int:
    """
    簡單將中文數字轉換為阿拉伯數字（僅支援常見格式）。
    注意：較複雜的中文數字轉換可能需要更完整的實現。
    """
    cn = cn.strip()
    num_map = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    unit_map = {'十': 10, '百': 100, '千': 1000, '萬': 10000, '億': 100000000}
    result = 0
    tmp = 0
    unit = 1
    # 從右向左解析
    for char in reversed(cn):
        if char in num_map:
            tmp += num_map[char] * unit
        elif char in unit_map:
            unit = unit_map[char]
            if unit >= 10000:
                result += tmp * unit
                tmp = 0
                unit = 1
            else:
                if tmp == 0:
                    tmp = 1 * unit
                else:
                    tmp = tmp * unit
                unit = 1
    result += tmp
    return result

def convert_amount(amount_str: str) -> int:
    """
    將金額字串轉換為阿拉伯數字，支援半形、全形以及中文數字格式。
    """
    s = fullwidth_to_halfwidth(amount_str)
    # 如果含有中文數字，則使用中文轉換
    if re.search(r"[零一二三四五六七八九十百千萬億]", s):
        try:
            return chinese_to_arabic(s)
        except Exception as e:
            return 0
    else:
        try:
            return int(s.replace(",", ""))
        except Exception as e:
            return 0

# --------------------
# 新增函式：預處理「請求賠償的事實根據」文本
# --------------------
def preprocess_compensation_claim(text: str) -> str:
    """
    對「請求賠償的事實根據」文本進行預處理與格式標準化：
    1. 清除多餘空白與換行符號。
    2. 將文本依據換行拆分成多行，並自動補上順序編號（若該行沒有以數字與句點開頭）。
    3. 忽略以「總計」開頭的行。
    回傳標準化後的文本。
    """
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\r\n|\r', '\n', text)
    text = text.strip()
    lines = text.split('\n')
    standardized_lines = []
    counter = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("總計"):
            continue
        if not re.match(r'^\d+\.\s*', line):
            line = f"{counter}. {line}"
            counter += 1
        else:
            line = re.sub(r'^\d+\.\s*', f"{counter}. ", line)
            counter += 1
        standardized_lines.append(line)
    standardized_text = "\n".join(standardized_lines)
    return standardized_text

# --------------------
# 新增函式：解析損害項目明細
# --------------------
def parse_damage_items_details(damage_text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    解析損害項目文本，提取每位原告的損害項目明細。
    
    預期格式：
      原告A：
      1. 項目名稱：金額元 [（請求理由）]
      2. 項目名稱：金額元 [（請求理由）]
      
      原告B：
      1. 項目名稱：金額元 [（請求理由）]
      ...
    
    若律師輸入的原告只有一名且未提供名稱，則自動設定為 "原告"。
    
    輸出結構：
      {
         "原告A": [
             {"item": "項目名稱", "amount": 數值, "reason": "請求理由"},
             ...
         ],
         "原告": [ ... ]
      }
    """
    result = {}
    sections = re.findall(r"原告\s*([^：:]*?)[：:](.*?)(?=原告\s*[^：:]*[：:]|$)", damage_text, re.S)
    for plaintiff, content in sections:
        name = plaintiff.strip() if plaintiff.strip() else "原告"
        items = []
        lines = content.strip().splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("總計"):
                i += 1
                continue
            m = re.match(r"^\d+\.\s*(.+?)[：:]\s*([\d,０-９]+)元(?:\s*(.*))?$", line)
            if m:
                item_name = m.group(1).strip()
                amount_str = m.group(2).strip()
                reason = m.group(3).strip() if m.group(3) else ""
                if not reason and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith("查"):
                        reason = next_line
                        i += 1
                amount = convert_amount(amount_str)
                items.append({
                    "item": item_name,
                    "amount": amount,
                    "reason": reason
                })
            i += 1
        result[name] = items
    return result

# --------------------
# LegalDocumentGenerator 類別
# --------------------
class LegalDocumentGenerator:
    def __init__(self):
        load_dotenv()
        try:
            self.embedding_model = KGVectorizer()
        except Exception as e:
            raise Exception(f"Error initializing KGVectorizer: {e}")
        try:
            self.es_manager = ElasticsearchManager(
                host="http://localhost:9201",
                username=os.getenv("ELASTIC_USER", "elastic"),
                password=os.getenv("ELASTIC_PASSWORD", "*3D7+GFIdBOT-glzYMLx"),
                verify_certs=False
            )
        except Exception as e:
            raise Exception(f"Error initializing ElasticsearchManager: {e}")
        try:
            self.neo4j_manager = Neo4jManager(
                uri=os.getenv("NEO4J_URI"),
                user=os.getenv("NEO4J_USER"),
                password=os.getenv("NEO4J_PASSWORD")
            )
        except Exception as e:
            raise Exception(f"Error initializing Neo4jManager: {e}")
        try:
            self.llm = OllamaLLM(
                model="kenneth85/llama-3-taiwan:8b-instruct-dpo",
                temperature=0.1,
                keep_alive=0
            )
        except Exception as e:
            raise Exception(f"Error initializing LLM: {e}")
        self.lawsuit_template = (
            "一、事實概述：\n{case_facts}\n\n"
            "二、法律依據：\n{legal_reference}\n\n"
            "三、損害項目：\n{damage_items}\n\n"
            "四、結論：\n{conclusion}"
        )
        self.damage_prompt = """
請根據以下輸入資料，動態生成【損害項目】段落。請將各項損害條列式列出，並注意以下要求：
1. 若有多位原告，請以「原告OOO：」區分，接著逐項損害條列。
2. 每項損害請直接給出金額，新台幣金額格式例如「38,706元」或「38,706元」。
3. 若未提及某損害類型，請勿臆造。
4. 請勿重複敘述同一個損害項目。
以下為相關輸入資料：
{input_text}
"""
        self.conclusion_prompt = """
請根據下列「原告名稱與損害金額」生成【結論】段落：
{plaintiffs_info}

請依以下格式與要求撰寫：
1. 以「綜上所陳」開頭，並概括各原告請求金額。
2. 若僅有一位原告，格式為「原告請求被告賠償總計……元」。
3. 若多位原告，格式為「共X位原告請求被告連帶賠償總計……元」。
4. 最後附註「自起訴狀送達翌日起至清償日止，按年利率5%計算法定利息」。
5. 請勿重複重點句子，例如「被告應負賠償責任」等在本段中僅出現一次即可。
"""

    def split_input(self, user_input: str) -> Dict[str, str]:
        patterns = {
            "case_facts": r"一[、\.．]\s*事故發生緣由[:：]\s*(.+?)(?=\n\s*二[、\.．]|$)",
            "injury_details": r"二[、\.．]\s*原告受傷情形[:：]\s*(.+?)(?=\n\s*三[、\.．]|$)",
            "compensation_request": r"三[、\.．]\s*請求賠償的事實根據[:：]\s*(.+)"
        }
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, user_input, re.S | re.M)
            result[key] = match.group(1).strip() if match else ""
        return result

    def generate_dynamic_legal_reference(self, case_facts: str, injury_details: str, compensation_request: str) -> str:
        legal_mapping = {
            "民法第184條第1項前段": ["未注意", "過失", "損害賠償", "侵害他人之權利"],
            "民法第185條": ["共同侵害", "共同行為", "數人侵害", "造意人"],
            "民法第187條": ["無行為能力", "限制行為能力", "法定代理人", "識別能力", "未成年"],
            "民法第188條": ["受僱人", "僱用人", "雇傭", "連帶賠償"],
            "民法第191-2條": ["汽車", "機車", "交通事故", "傷害", "損害"],
            "民法第193條第1項": ["損失", "醫療費用", "工作", "薪資", "就醫", "傷"],
            "民法第195條第1項前段": ["精神", "慰撫金", "痛苦", "名譽", "健康", "隱私", "貞操"],
            "民法第213條": ["回復原狀", "給付金錢", "損害發生"],
            "民法第216條": ["填補損害", "所失利益", "預期利益"],
            "民法第217條": ["被害人與有過失", "賠償金減輕", "重大損害原因"]
        }
        legal_references = []
        for law, keywords in legal_mapping.items():
            if any(term in case_facts for term in keywords):
                legal_references.append(law)
            if any(term in injury_details for term in keywords):
                legal_references.append(law)
            if any(term in compensation_request for term in keywords):
                legal_references.append(law)
        legal_references = list(set(legal_references))
        if not legal_references:
            return "目前未找到相關法律條文，請檢查輸入內容是否正確。"
        law_descriptions = {
            "民法第184條第1項前段": "「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」",
            "民法第185條": "「數人共同不法侵害他人之權利者，連帶負損害賠償責任。」",
            "民法第187條": "「無行為能力人或限制行為能力人，不法侵害他人之權利者，由其法定代理人負賠償責任。」",
            "民法第188條": "「受僱人因執行職務，不法侵害他人之權利者，由僱用人與行為人連帶負損害賠償責任。」",
            "民法第191-2條": "「汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。」",
            "民法第193條第1項": "「不法侵害他人之身體或健康者，應負損害賠償責任。」",
            "民法第195條第1項前段": "「不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人亦得請求賠償相當之金額。」",
            "民法第213條": "「負損害賠償責任者，應回復損害發生前之原狀。」",
            "民法第216條": "「損害賠償以填補受損害者所受損害及所失利益為限。」",
            "民法第217條": "「損害之發生或擴大，被害人與有過失者，法院得減輕賠償金額。」"
        }
        references_text = "；".join([law_descriptions[law] for law in legal_references])
        references_text += "；" + "、".join(legal_references) + "分別定有明文。"
        references_text += "查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任："
        print("Matched Legal References:", legal_references)
        print("Generated References Text:", references_text)
        return references_text
    
    def get_lawyer_input_by_case_id(self, case_id: int) -> str:
        """從 ES 裡查出指定 case_id 的模擬律師輸入（label=LawyerInput）"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"case_id": case_id}},
                        {"term": {"label": "LawyerInput"}}
                    ]
                }
            }
        }
        try:
            result = self.es_manager.client.search(index="legal_knowledge_graph", body=query, size=1)
            hits = result.get("hits", {}).get("hits", [])
            if hits:
                return hits[0]["_source"].get("text", "無")  # ✅ 改為抓 text 欄位
            return "無"
        except Exception as e:
            print(f"⚠️ 查詢 lawyer_input 失敗（case_id={case_id}）：{e}")
            return "無"



    def generate_dynamic_legal_reference_combined(self, case_facts: str, injury_details: str, compensation_request: str) -> str:
        """
        混合關鍵字匹配與 RAG 結果，RAG 只用於相似案例顯示，不影響法律依據段落。
        """
        keyword_result = self.generate_dynamic_legal_reference(case_facts, injury_details, compensation_request)
        combined_text = " ".join([case_facts, injury_details, compensation_request])
        embedding = self.embedding_model.embed_texts([combined_text])[0]
        try:
            rag_results = self.es_manager.search_similar(embedding, top_k=5)
        except Exception as e:
            print(f"RAG 檢索失敗：{e}")
            return keyword_result

        similar_cases = []
        for r in rag_results:
            source = r.get("_source", {})
            text = source.get("text", "").strip()
            case_id = source.get("case_id", "未知")
            lawyer_input = self.get_lawyer_input_by_case_id(case_id)
            if text:
                similar_cases.append({
                    "case_id": case_id,
                    "lawyer_input": lawyer_input,
                    "excerpt": text
                })

        # 顯示前三筆相似案例
        if similar_cases:
            print("前三筆相似案例：")
            for idx, case in enumerate(similar_cases[:3], 1):
                print(f"案例 {idx}:")
                print(f"  case_id: {case['case_id']}")
                print(f"  模擬律師輸入: {case['lawyer_input']}")
                print(f"  起訴書節錄: {case['excerpt']}")

        return keyword_result

    def generate_damage_items(self, input_data: Dict[str, str]) -> str:
        compensation_request_raw = input_data.get("compensation_request", "")
        compensation_request_std = preprocess_compensation_claim(compensation_request_raw)
        
        input_text = "\n".join([
            "事故發生經過：",
            input_data.get("case_facts", ""),
            "\n原告受傷情形：",
            input_data.get("injury_details", ""),
            "\n請求依據：",
            compensation_request_std
        ])

        prompt_text = self.damage_prompt.format(input_text=input_text)
        chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(input_variables=["input_text"], template=prompt_text)
        )
        result = chain.run({"input_text": input_text})
        result = re.sub(r"[\*\#]+", "", result)
        return result.strip()

    def generate_conclusion(self, damage_text: str) -> str:
        """
        生成結論：
        1. 利用 parse_damage_items_details 解析出每位原告的損害項目明細（僅取金額）。
        2. 分別計算各原告各項金額總和，並計算所有原告總計。
        數字部分以千位逗號格式顯示，例如 123,456元。
        若無法解析金額則給出預設結論。
        """
        details = parse_damage_items_details(damage_text)
        if not details or all(len(items) == 0 for items in details.values()):
            return (
                "綜上所陳，原告請求被告應負損害賠償責任，並自起訴狀送達翌日起至清償日止，"
                "按年利率5%計算法定利息，特此敘明。"
            )
        lines = []
        overall_total = 0
        for plaintiff, items in details.items():
            total = sum(item["amount"] for item in items)
            overall_total += total
            item_amounts = " + ".join(f"{format(item['amount'], ',')}元" for item in items if item["amount"] > 0)
            lines.append(f"原告 {plaintiff} 之損害金額：{item_amounts} = {format(total, ',')}元")
        if len(details) > 1:
            lines.append(f"共{len(details)}位原告請求被告連帶賠償總計：{format(overall_total, ',')}元")
        else:
            lines.append(f"原告請求被告賠償總計：{format(overall_total, ',')}元")
        prompt_text = self.conclusion_prompt.format(
            plaintiffs_info="\n".join(lines)
        )
        chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(input_variables=["plaintiffs_info"], template=prompt_text)
        )
        result = chain.run({"plaintiffs_info": "\n".join(lines)})
        result = re.sub(r"[\*\#]+", "", result)
        return result.strip()

    def generate_full_lawsuit(self, user_input: str) -> str:
        input_data = self.split_input(user_input)
        case_facts = input_data.get("case_facts", "").strip()
        if not case_facts:
            case_facts = "（未提供事故發生緣由，請補充）"
        else:
            if not case_facts.startswith("緣"):
                case_facts = "緣" + case_facts
        legal_reference = self.generate_dynamic_legal_reference_combined(
            case_facts,
            input_data.get("injury_details", ""),
            input_data.get("compensation_request", "")
        )
        if "請自行檢核" not in legal_reference and "目前未找到" not in legal_reference:
            legal_reference += "\n\n綜上，依上述規定被告應負損害賠償責任。"
        damage_items = self.generate_damage_items(input_data)
        conclusion = self.generate_conclusion(damage_items)
        final_text = self.lawsuit_template.format(
            case_facts=case_facts,
            legal_reference=legal_reference,
            damage_items=damage_items,
            conclusion=conclusion
        )
        final_text = re.sub(r"[\*\#]+", "", final_text)
        return final_text

    def process_excel(self, file_path: str):
        df = pd.read_excel(file_path, engine="openpyxl")
        if "律師輸入" not in df.columns or "生成內容" not in df.columns:
            print("Excel 應包含 '律師輸入' 與 '生成內容' 欄位")
            return
        for i, row in df.iterrows():
            if pd.notna(row['律師輸入']):
                user_input = str(row['律師輸入'])
                try:
                    final_text = self.generate_full_lawsuit(user_input)
                    print(f"第 {i+1} 筆生成結果：\n{final_text}\n")
                    df.at[i, "生成內容"] = final_text
                except Exception as e:
                    print(f"⚠️ 第 {i+1} 筆處理失敗：{e}")
                    df.at[i, "生成內容"] = "⚠️ 生成失敗"
        out_path = file_path.replace(".xlsx", "_結果.xlsx")
        df.to_excel(out_path, index=False, engine="openpyxl")
        print(f"✅ 已儲存至 {out_path}")

if __name__ == "__main__":
    file_path = input("📂 請輸入 Excel 檔案路徑：").strip()
    generator = LegalDocumentGenerator()
    generator.process_excel(file_path)
