"""
KG_560_extract_structured_info.py
使用LLM從段落中提取結構化信息

執行順序: 在KG_500之後、KG_600之前執行
輸入: Neo4j知識圖譜
輸出: structured_summaries.jsonl
"""

import json
import logging
import os
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Neo4j連線
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Ollama API設定
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"  # 使用你專案的預設模型

def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """
    呼叫Ollama API

    Args:
        prompt: 用戶提示
        system_prompt: 系統提示

    Returns:
        LLM的回覆文本
    """
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2000
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        logger.error(f"Ollama API呼叫失敗: {str(e)}")
        return ""


class StructuredInfoExtractor:
    """結構化信息提取器"""

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        logger.info("✅ 成功連接至 Neo4j")

    def close(self):
        self.driver.close()

    def extract_fact_info(self, text: str) -> Dict[str, Any]:
        """提取事實段落的結構化信息"""

        prompt = f"""請從以下交通事故事實描述中，提取結構化信息。

**重要規則**：
1. 只提取具體的時間（如"2024年3月15日上午10時許"），不要提取模糊詞（如"當時"、"事發後"）
2. 只提取文中明確出現的信息，不要推測
3. 如果某項信息不存在，該欄位填null

事實描述：
{text}

請以JSON格式回答：
{{
  "time_info": "2024年3月15日上午10時許",  // 具體時間，不要"當時"等模糊詞
  "location_info": "台北市中正區重慶南路一段122號前",  // 事故地點
  "parties": {{
    "plaintiff": {{
      "name": "甲○○",
      "vehicles": ["車牌ABC-1234自小客車"],
      "role": "直行車輛駕駛"
    }},
    "defendant": {{
      "name": "乙○○",
      "vehicles": ["車牌XYZ-5678機車"],
      "role": "左轉車輛駕駛"
    }}
  }},
  "accident_process": {{
    "defendant_fault": ["未注意車前狀況", "貿然左轉"],
    "plaintiff_action": ["正常直行"],
    "collision_manner": "被告左轉車輛撞擊原告直行車輛右前側"
  }},
  "injuries": [
    {{
      "person": "原告",
      "injury_description": "頭部外傷、右小腿骨折",
      "treatment": "需手術治療"
    }}
  ],
  "evidence": {{
    "witnesses": ["證人王○○"],
    "documents": ["診斷證明書", "事故鑑定書"]
  }}
}}

回答（只要JSON，不要包含註解）："""

        try:
            system_prompt = "你是一位專業的法律文書分析助手，擅長從事實描述中提取結構化信息。請只回答JSON格式，不要包含其他文字。"
            response_text = call_ollama(prompt, system_prompt)

            # 嘗試解析JSON（可能包含markdown代碼塊）
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())
            return result

        except Exception as e:
            logger.error(f"❌ LLM提取失敗: {str(e)}")
            return {}

    def extract_laws_info(self, text: str) -> Dict[str, Any]:
        """提取法條段落的結構化信息"""

        prompt = f"""請從以下法條引用段落中，提取結構化信息。

**重要**：這是起訴書，不是判決書，不要提取法院的責任認定，只提取原告的主張。

法條引用：
{text}

請以JSON格式回答：
{{
  "applicable_laws": [
    {{
      "article": "民法第184條第1項前段",
      "reason": "因過失侵害他人權利",
      "supporting_facts": ["被告未注意車前狀況"]
    }},
    {{
      "article": "民法第195條第1項前段",
      "reason": "侵害身體健康",
      "supporting_facts": ["造成原告頭部外傷、骨折"]
    }}
  ],
  "law_chain": ["184-1前段", "193-1", "195-1前段"]  // 法條適用順序
}}

回答（只要JSON，不要包含註解）："""

        try:
            system_prompt = "你是法律分析專家。請只回答JSON格式，不要包含其他文字。"
            response_text = call_ollama(prompt, system_prompt)

            # 清理markdown代碼塊
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            return json.loads(response_text.strip())
        except Exception as e:
            logger.error(f"❌ 法條提取失敗: {str(e)}")
            return {}

    def extract_compensation_info(self, text: str) -> Dict[str, Any]:
        """提取賠償段落的結構化信息"""

        prompt = f"""請從以下損害賠償段落中，提取結構化信息。

**重要規則**：
1. 只提取文中實際出現的賠償項目，不要猜測或添加不存在的項目
2. item欄位請完整保留原文的項目名稱，不要改寫或標準化
3. supporting_text要包含該項目的完整描述句子

賠償內容：
{text}

請以JSON格式回答：
{{
  "expenses": [
    {{
      "item": "醫療費用",  // 項目名稱（完整保留原文，不要改寫）
      "amount": 150000,  // 金額（整數）
      "supporting_text": "原告因本次事故支出醫療費用150,000元，有收據可證"  // 支持該項目的完整原文句子
    }},
    {{
      "item": "精神慰撫金",
      "amount": 300000,
      "supporting_text": "原告因此精神痛苦，請求精神慰撫金300,000元"
    }}
    // 只列出實際存在的項目！不要添加不存在的項目！
  ],
  "total_claimed": 450000,  // 請求總額（如果有明確提到）
  "deductions": [
    {{
      "reason": "已給付之強制險理賠金",
      "amount": 50000
    }}
  ]  // 扣除項目（如果有）
}}

回答（只要JSON，不要包含註解）："""

        try:
            system_prompt = "你是法律財務分析專家。請只回答JSON格式，不要包含其他文字。"
            response_text = call_ollama(prompt, system_prompt)

            # 清理markdown代碼塊
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            return json.loads(response_text.strip())
        except Exception as e:
            logger.error(f"❌ 賠償提取失敗: {str(e)}")
            return {}

    def extract_conclusion_info(self, text: str) -> Dict[str, Any]:
        """提取結論段落的結構化信息"""

        prompt = f"""請從以下起訴書結論段落中，提取結構化信息。

**重要**：這是起訴書的結論，只提取原告的請求，不要提取法院認定的金額。

結論：
{text}

請以JSON格式回答：
{{
  "total_claimed": 735000,  // 原告請求總額
  "interest": {{
    "rate": "年息5%",
    "start_date": "起訴狀繕本送達翌日"
  }},
  "litigation_costs": "請求由被告負擔",
  "payment_terms": "請求一次給付"
}}

回答（只要JSON，不要包含註解）："""

        try:
            system_prompt = "你是法律分析專家。請只回答JSON格式，不要包含其他文字。"
            response_text = call_ollama(prompt, system_prompt)

            # 清理markdown代碼塊
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            return json.loads(response_text.strip())
        except Exception as e:
            logger.error(f"❌ 結論提取失敗: {str(e)}")
            return {}

    def process_all_cases(self, output_file: str = "structured_summaries.jsonl", limit: int = None):
        """處理所有案件，生成結構化摘要JSONL

        Args:
            output_file: 輸出檔案路徑
            limit: 限制處理的案件數量（測試用），None表示處理全部
        """

        query = """
        MATCH (c:Case)
        OPTIONAL MATCH (c)-[:包含]->(f:Facts)
        OPTIONAL MATCH (c)-[:包含]->(f)-[:適用]->(l:Laws)
        OPTIONAL MATCH (c)-[:包含]->(f)-[:適用]->(l)-[:計算]->(comp:Compensation)
        OPTIONAL MATCH (c)-[:包含]->(f)-[:適用]->(l)-[:計算]->(comp)-[:推導]->(con:Conclusion)
        OPTIONAL MATCH (c)-[:包含]->(li:LawyerInput)
        OPTIONAL MATCH (li)-[:因]->(cause:LawyerInput_Cause)
        OPTIONAL MATCH (li)-[:果]->(effect:LawyerInput_Effect)
        RETURN
            c.case_id AS case_id,
            f.description AS indictment_fact,
            l.description AS indictment_laws,
            comp.description AS indictment_compensation,
            con.description AS indictment_conclusion,
            li.lawyer_input AS lawyer_input_fact,
            cause.description AS lawyer_input_cause,
            effect.description AS lawyer_input_injury
        ORDER BY c.case_id
        """

        if limit:
            query += f" LIMIT {limit}"

        with self.driver.session() as session:
            results = session.run(query)

            with open(output_file, 'w', encoding='utf-8') as f:
                for record in results:
                    case_id = record["case_id"]
                    logger.info(f"🔄 處理案件 {case_id}...")

                    # 處理7個段落
                    case_data = []

                    # 1. 起訴書事實
                    if record["indictment_fact"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "indictment_fact",
                            "original_text": record["indictment_fact"],
                            "structured_info": self.extract_fact_info(record["indictment_fact"])
                        })

                    # 2. 起訴書法條
                    if record["indictment_laws"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "indictment_laws",
                            "original_text": record["indictment_laws"],
                            "structured_info": self.extract_laws_info(record["indictment_laws"])
                        })

                    # 3. 起訴書賠償
                    if record["indictment_compensation"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "indictment_compensation",
                            "original_text": record["indictment_compensation"],
                            "structured_info": self.extract_compensation_info(record["indictment_compensation"])
                        })

                    # 4. 起訴書結論
                    if record["indictment_conclusion"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "indictment_conclusion",
                            "original_text": record["indictment_conclusion"],
                            "structured_info": self.extract_conclusion_info(record["indictment_conclusion"])
                        })

                    # 5-7. 律師輸入 (這三個可以用類似fact的提取邏輯)
                    if record["lawyer_input_fact"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "lawyer_input_fact",
                            "original_text": record["lawyer_input_fact"],
                            "structured_info": self.extract_fact_info(record["lawyer_input_fact"])
                        })

                    if record["lawyer_input_cause"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "lawyer_input_cause",
                            "original_text": record["lawyer_input_cause"],
                            "structured_info": {}  # 可選擇性提取
                        })

                    if record["lawyer_input_injury"]:
                        case_data.append({
                            "case_id": case_id,
                            "paragraph_type": "lawyer_input_injury",
                            "original_text": record["lawyer_input_injury"],
                            "structured_info": {}  # 可選擇性提取
                        })

                    # 寫入JSONL
                    for paragraph_data in case_data:
                        f.write(json.dumps(paragraph_data, ensure_ascii=False) + '\n')

                    logger.info(f"✅ 案件 {case_id} 完成，共 {len(case_data)} 個段落")

        logger.info(f"🎉 所有案件處理完成！輸出至 {output_file}")


if __name__ == "__main__":
    import sys

    extractor = StructuredInfoExtractor()
    try:
        # 檢查是否有命令行參數
        if len(sys.argv) > 1:
            # 使用命令行參數作為limit
            limit = int(sys.argv[1])
            output_file = f"structured_summaries_test_{limit}.jsonl"
            logger.info(f"🧪 測試模式：只處理前 {limit} 個案件")
        else:
            # 互動模式
            mode = input("選擇模式 (1=測試模式/2=全部處理): ").strip()
            if mode == "1":
                limit = int(input("要處理幾個案件? (建議3-5個): ").strip())
                output_file = f"structured_summaries_test_{limit}.jsonl"
                logger.info(f"🧪 測試模式：處理 {limit} 個案件")
            else:
                limit = None
                output_file = "structured_summaries.jsonl"
                confirm = input("⚠️  將處理所有案件，確定嗎? (y/n): ").strip().lower()
                if confirm != 'y':
                    logger.info("❌ 已取消")
                    exit(0)

        extractor.process_all_cases(output_file=output_file, limit=limit)

        logger.info(f"\n✅ 完成！輸出檔案：{output_file}")
        logger.info("📝 請檢查輸出檔案確認提取品質")

    finally:
        extractor.close()
