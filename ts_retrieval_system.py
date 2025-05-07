# ts_retrieval_system.py
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from typing import List, Dict, Tuple, Optional, Union
import re
import time
import os
from dotenv import load_dotenv
import requests
from ts_models import EmbeddingModel
from ts_define_case_type import get_case_type
from ts_prompt import (
    get_facts_prompt, 
    get_compensation_prompt_part1_single_plaintiff,     # Add this
    get_compensation_prompt_part1_multiple_plaintiffs,  # Add this
    get_compensation_prompt_part2,
    get_compensation_prompt_part3,
    get_case_summary_prompt
)
from ts_prompt_check import (
    get_fact_quality_check_prompt,
    get_compensation_part1_check_prompt,
    get_calculation_tags_check_prompt
)

class RetrievalSystem:
    def __init__(self, modelname = "gemma3:27b"):
        """Initialize connections to Elasticsearch, Neo4j, and the embedding model"""
        load_dotenv()
        try:
            # Initialize Elasticsearch
            self.es = Elasticsearch(
                "https://localhost:9209",
                http_auth=(os.getenv('ELASTIC_USER'), os.getenv('ELASTIC_PASSWORD')),
                verify_certs=False
            )
            self.es_index = 'ts_text_embeddings'
            
            # Test Elasticsearch connection
            if not self.es.ping():
                raise ConnectionError("無法連接到 Elasticsearch")
            
            # Initialize Neo4j
            self.neo4j_driver = GraphDatabase.driver(
                os.getenv('NEO4J_URI'),
                auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
            )
            
            # Test Neo4j connection
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            
            # Initialize embedding model
            self.embedding_model = EmbeddingModel()
            
            # Initialize LLM API settings
            self.llm_url = "http://localhost:11434/api/generate"
            self.llm_model = modelname #"gemma3:27b" #"kenneth85/llama-3-taiwan:8b-instruct-dpo"
            
            # Test LLM connection
            response = requests.get("http://localhost:11434/api/version")
            if response.status_code != 200:
                raise ConnectionError("無法連接到 Ollama API")
            
            print("成功連接所有服務")
            
        except Exception as e:
            print(f"初始化錯誤: {str(e)}")
            raise
    
    def close(self):
        """Close connections"""
        if hasattr(self, 'neo4j_driver') and self.neo4j_driver:
            self.neo4j_driver.close()
    
    def search_elasticsearch(self, query_text: str, search_type: str, k: int, query_case_type: str) -> List[Dict]:
        """
        Search Elasticsearch for similar documents of the specified type and case type
        
        Args:
        query_text: The text to search for
        search_type: Either "full" or "fact"
        k: Number of top results to retrieve
        query_case_type: The case type determined from the query           
            
        Returns:
            List of dictionaries containing case_id, score, and text
        """
        try:
            # Case type is now passed as parameter instead of being determined here
            print(f"使用案件類型進行搜索: {query_case_type}")

            # Create the embedding for the query
            query_embedding = self.embedding_model.embed_texts([query_text])[0]

            # Search in Elasticsearch with case_type filter
            script_query = {
                "script_score": {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"text_type": search_type}},
                                {"term": {"case_type": query_case_type}}
                            ]
                        }
                    },
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding.tolist()}
                    }
                }
            }
            
            response = self.es.search(
                index=self.es_index,
                body={
                    "size": k,
                    "query": script_query,
                    "_source": ["case_id", "text", "chunk_id", "text_type", "case_type"]
                }
            )
            
            # Process results
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "case_id": hit["_source"]["case_id"],
                    "score": hit["_score"],
                    "text": hit["_source"]["text"],
                    "chunk_id": hit["_source"]["chunk_id"],
                    "text_type": hit["_source"]["text_type"],
                    "case_type": hit["_source"].get("case_type", "")  # Get case_type if available
                })
            
            # If no results found with the exact case type, try a more generic search
            if not results:
                print(f"在 {query_case_type} 類別中無相符結果，嘗試通用搜索...")
                # Use original search without case_type filter
                script_query = {
                    "script_score": {
                        "query": {"term": {"text_type": search_type}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_embedding.tolist()}
                        }
                    }
                }
                
                response = self.es.search(
                    index=self.es_index,
                    body={
                        "size": k,
                        "query": script_query,
                        "_source": ["case_id", "text", "chunk_id", "text_type", "case_type"]
                    }
                )
                
                # Process results
                for hit in response["hits"]["hits"]:
                    results.append({
                        "case_id": hit["_source"]["case_id"],
                        "score": hit["_score"],
                        "text": hit["_source"]["text"],
                        "chunk_id": hit["_source"]["chunk_id"],
                        "text_type": hit["_source"]["text_type"],
                        "case_type": hit["_source"].get("case_type", "")  # Get case_type if available
                    })
            
            return results
        
        except Exception as e:
            print(f"搜索 Elasticsearch 時發生錯誤: {str(e)}")
            raise
    
    #FOR ts_gradio_app.py
    def get_full_text_from_elasticsearch(self, case_id):
        """Get full text for a case from Elasticsearch"""
        try:
            query = {
                "bool": {
                    "must": [
                        {"term": {"case_id": case_id}},
                        {"term": {"text_type": "full"}}
                    ]
                }
            }
            
            response = self.es.search(
                index=self.es_index,
                body={
                    "size": 1,
                    "query": query,
                    "_source": ["case_id", "text", "chunk_id", "text_type"]
                }
            )
            
            if response["hits"]["total"]["value"] > 0:
                return response["hits"]["hits"][0]["_source"]["text"]
            else:
                return f"無法獲取 Case ID {case_id} 的完整文本"
        except Exception as e:
            return f"無法獲取 Case ID {case_id} 的完整文本: {str(e)}"

    def get_laws_from_neo4j(self, case_ids: List[int]) -> List[Dict]:
        """
        Retrieve used laws for the given case ids from Neo4j
        
        Args:
            case_ids: List of case ids
            
        Returns:
            List of dictionaries containing law information
        """
        try:
            with self.neo4j_driver.session() as session:
                # Query to get laws related to these cases
                query = """
                MATCH (c:case_node {case_id: $case_id})-[:used_law_relation]->(l:law_node)
                RETURN l.number AS law_number, l.content AS law_content
                """
                
                laws = []
                for case_id in case_ids:
                    result = session.run(query, case_id=case_id)
                    for record in result:
                        laws.append({
                            "case_id": case_id,
                            "law_number": record["law_number"],
                            "law_content": record["law_content"]
                        })
                
                return laws
        
        except Exception as e:
            print(f"從 Neo4j 獲取法條時發生錯誤: {str(e)}")
            raise
    
    def get_conclusions_from_neo4j(self, case_ids: List[int]) -> List[Dict]:
        """
        Retrieve conclusions for the given case ids from Neo4j
        
        Args:
            case_ids: List of case ids
            
        Returns:
            List of dictionaries containing conclusion information
        """
        try:
            with self.neo4j_driver.session() as session:
                # Query to get conclusions related to these cases
                query = """
                MATCH (c:case_node {case_id: $case_id})-[:conclusion_text_relation]->(conc:conclusion_text)
                RETURN conc.chunk AS conclusion_text
                """
                
                conclusions = []
                for case_id in case_ids:
                    result = session.run(query, case_id=case_id)
                    for record in result:
                        conclusions.append({
                            "case_id": case_id,
                            "conclusion_text": record["conclusion_text"]
                        })
                
                return conclusions
        
        except Exception as e:
            print(f"從 Neo4j 獲取結論時發生錯誤: {str(e)}")
            raise
    
    def count_law_occurrences(self, laws: List[Dict]) -> Dict[str, int]:
        """
        Count law occurrences and return a dictionary with counts
        
        Args:
            laws: List of law dictionaries
            
        Returns:
            Dictionary with law numbers as keys and occurrence counts as values
        """
        law_counts = {}
        for law in laws:
            law_number = law["law_number"]
            if law_number in law_counts:
                law_counts[law_number] += 1
            else:
                law_counts[law_number] = 1
        
        return law_counts
    
    def filter_laws_by_occurrence(self, law_counts: Dict[str, int], threshold: int) -> List[str]:
        """
        Filter laws by occurrence threshold and sort them in ascending numerical order
        
        Args:
            law_counts: Dictionary with law numbers as keys and occurrence counts as values
            threshold: Minimum number of occurrences required
            
        Returns:
            List of law numbers that meet the threshold, sorted in ascending order
        """
        # Filter laws that meet the threshold
        filtered_laws = [law for law, count in law_counts.items() if count >= threshold]
        
        # Sort the laws numerically (handling hyphenated law numbers like "184-1")
        def law_sort_key(law_num):
            # Split by hyphen if exists
            parts = law_num.split('-')
            # Convert main number to int
            main_num = int(parts[0])
            # If there's a sub-number, convert it to int too, otherwise use 0
            sub_num = int(parts[1]) if len(parts) > 1 else 0
            # Return a tuple for sorting
            return (main_num, sub_num)
        
        # Sort the filtered laws using the custom sort key
        return sorted(filtered_laws, key=law_sort_key)
    
    def get_law_contents(self, law_numbers: List[str]) -> List[Dict]:
        """
        Retrieve law contents for the given law numbers from Neo4j
        
        Args:
            law_numbers: List of law numbers
            
        Returns:
            List of dictionaries containing law number and content
        """
        try:
            with self.neo4j_driver.session() as session:
                laws = []
                for number in law_numbers:
                    query = """
                    MATCH (l:law_node {number: $number})
                    RETURN l.number AS number, l.content AS content
                    """
                    result = session.run(query, number=number)
                    for record in result:
                        laws.append({
                            "number": record["number"],
                            "content": record["content"]
                        })
                
                return laws
        
        except Exception as e:
            print(f"從 Neo4j 獲取法條內容時發生錯誤: {str(e)}")
            raise
    
    def extract_compensation_amount(self, text: str) -> Optional[float]:
        """
        Extract compensation amount from conclusion text
        
        Args:
            text: Conclusion text
            
        Returns:
            Compensation amount as float, or None if not found
        """
        # Multiple patterns to catch different formats
        patterns = [
            r'(?:共計|總計|合計|統計)(?:新臺幣)?(?:\s)*(\d{1,3}(?:,\d{3})*|\d+)(?:\.?\d+)?(?:\s)*元',
            r'(?:賠償金額)?(?:合計|共計|總計)(?:\s)*(\d{1,3}(?:,\d{3})*|\d+)(?:\.?\d+)?(?:\s)*元',
            r'賠償(?:金額)?(?:\s)*(\d{1,3}(?:,\d{3})*|\d+)(?:\.?\d+)?(?:\s)*元',
            r'合計(?:\s)*(\d{1,3}(?:,\d{3})*|\d+)(?:\.?\d+)?(?:\s)*元'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def calculate_average_compensation(self, conclusions: List[Dict]) -> float:
        """
        Calculate average compensation amount from conclusion texts
        
        Args:
            conclusions: List of conclusion dictionaries
            
        Returns:
            Average compensation amount
        """
        amounts = []
        for conclusion in conclusions:
            amount = self.extract_compensation_amount(conclusion["conclusion_text"])
            if amount is not None:
                amounts.append(amount)
        
        if amounts:
            return sum(amounts) / len(amounts)
        else:
            return 0.0
    
    def split_user_query(self, query_text: str) -> Dict[str, str]:
        """
        Split user query into sections based on markers with proper spacing
        
        Args:
            query_text: User query text
            
        Returns:
            Dictionary with sections
        """
        try:
            # Trim any leading/trailing whitespace
            query_text = query_text.strip()
            
            # Find positions of section markers
            pos_1 = query_text.find("一、")
            
            # For the second and third markers, we'll use regex to ensure there's whitespace before them
            matches_2 = list(re.finditer(r'(?:\s)二、', query_text))
            matches_3 = list(re.finditer(r'(?:\s)三、', query_text))
            
            # Check if all three markers exist
            if pos_1 == -1 or not matches_2 or not matches_3:
                print("警告: 無法正確識別文本標記。請確保格式為「一、」開頭，然後有「二、」和「三、」，且後兩者前面有空格或換行。")
                return {
                    "accident_facts": "",
                    "injuries": "",
                    "compensation_facts": ""
                }
            
            # Get positions (using the first match if multiple exist)
            pos_2 = matches_2[0].start() + 1  # +1 to point to the actual "二" character
            pos_3 = matches_3[0].start() + 1  # +1 to point to the actual "三" character
            
            # Check if they are in correct order
            if not (pos_1 < pos_2 < pos_3):
                print(f"警告: 標記順序錯誤：一、({pos_1}) 二、({pos_2}) 三、({pos_3})")
                return {
                    "accident_facts": "",
                    "injuries": "",
                    "compensation_facts": ""
                }
            
            # Extract the three parts
            accident_facts = query_text[pos_1:pos_2-1].strip()
            injuries = query_text[pos_2:pos_3-1].strip()
            compensation_facts = query_text[pos_3:].strip()
            
            return {
                "accident_facts": accident_facts,
                "injuries": injuries,
                "compensation_facts": compensation_facts
            }
        
        except Exception as e:
            print(f"分割查詢時發生錯誤: {str(e)}")
            raise
    
    def call_llm(self, prompt: str) -> str:
        """
        Call LLM with the given prompt
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            LLM response text
        """
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                return response.json()["response"].strip()
            else:
                raise Exception(f"LLM API 錯誤: {response.status_code}, {response.text}")
        
        except Exception as e:
            print(f"呼叫 LLM 時發生錯誤: {str(e)}")
            raise

    def get_indictment_from_neo4j(self, case_id: int) -> str:
        """
        Retrieve the full indictment text for a given case id from Neo4j

        Args:
            case_id: The case id to retrieve

        Returns:
            The full indictment text
        """
        try:
            with self.neo4j_driver.session() as session:
                query = """
                MATCH (c:case_node {case_id: $case_id})
                RETURN c.case_text AS indictment_text
                """

                result = session.run(query, case_id=case_id)
                record = result.single()

                print(f"NEAREST INDICTMENT 查詢結果: {record}")

                # Correct way to check Neo4j record
                if record is not None and record.get("indictment_text") is not None:
                    return record["indictment_text"]
                else:
                    print(f"警告: 在 Neo4j 中找不到案件 {case_id} 的起訴狀文本")
                    return ""

        except Exception as e:
            print(f"從 Neo4j 獲取起訴狀文本時發生錯誤: {str(e)}")
            raise

    def split_indictment_text(self, indictment_text: str) -> Dict[str, str]:
        """
        Split indictment text into fact, law, compensation, and conclusion parts
        using the same method as in create_indictment_nodes

        Args:
            indictment_text: The full indictment text

        Returns:
            Dictionary with the four parts
        """
        # Initialize section variables
        fact_text, law_text, compensation_text, conclusion_text = "", "", "", ""

        try:
            # Trim any leading/trailing whitespace
            indictment_text = indictment_text.strip()

            # Find positions of required markers
            pos_1 = indictment_text.find("一、")

            # For the second marker and "（一）"/"(一)", use regex to ensure there's whitespace before them
            matches_2 = list(re.finditer(r'(?:\s)二、', indictment_text))
            matches_section_1 = list(re.finditer(r'(?:\s)[（(]一[）)]', indictment_text))

            # For the conclusion, find either "綜上所陳" or "綜上所述"
            pos_conclusion_1 = indictment_text.find("綜上所陳")
            pos_conclusion_2 = indictment_text.find("綜上所述")

            # Use the one that appears in the text (prefer "綜上所陳" if both appear)
            if pos_conclusion_1 != -1:
                pos_conclusion = pos_conclusion_1
            elif pos_conclusion_2 != -1:
                pos_conclusion = pos_conclusion_2
            else:
                pos_conclusion = -1
                print("警告: 起訴狀中缺少「綜上所陳」或「綜上所述」標記")
                return {
                    "fact_text": "",
                    "law_text": "",
                    "compensation_text": "",
                    "conclusion_text": ""
                }

            # Check if all required markers exist
            if pos_1 == -1 or not matches_2 or not matches_section_1:
                print("警告: 起訴狀中缺少必要標記")
                return {
                    "fact_text": "",
                    "law_text": "",
                    "compensation_text": "",
                    "conclusion_text": ""
                }

            pos_2 = matches_2[0].start() + 1  # +1 to point to the actual "二" character
            pos_section_1 = matches_section_1[0].start() + 1  # +1 to point to the actual "（" or "(" character

            # Check if they are in correct order
            if not (pos_1 < pos_2 < pos_section_1 < pos_conclusion):
                print("警告: 起訴狀標記順序錯誤")
                return {
                    "fact_text": "",
                    "law_text": "",
                    "compensation_text": "",
                    "conclusion_text": ""
                }

            # Extract the content of the different parts
            fact_text = indictment_text[pos_1:pos_2-1].strip()
            law_text = indictment_text[pos_2:pos_section_1-1].strip()
            compensation_text = indictment_text[pos_section_1:pos_conclusion].strip()
            conclusion_text = indictment_text[pos_conclusion:].strip()

        except Exception as e:
            print(f"分割起訴狀文本時發生錯誤: {str(e)}")
            return {
                "fact_text": "",
                "law_text": "",
                "compensation_text": "",
                "conclusion_text": ""
            }

        return {
            "fact_text": fact_text,
            "law_text": law_text,
            "compensation_text": compensation_text,
            "conclusion_text": conclusion_text
        }
    
    def generate_case_summary(self, accident_facts: str, injuries: str) -> str:
        """
        Generate a summary of the case facts and injuries for quality check

        Args:
            accident_facts: The accident facts section from user query
            injuries: The injuries section from user query

        Returns:
            A summary of the case
        """
        prompt = get_case_summary_prompt(accident_facts, injuries)
        return self.call_llm(prompt)

    def check_fact_quality(self, generated_fact: str, summary: str) -> Dict[str, str]:
        """
        Check if the generated fact part matches the summary

        Args:
            generated_fact: The generated fact part
            summary: The case summary for comparison

        Returns:
            Dictionary with check result and reason
        """
        prompt = get_fact_quality_check_prompt(generated_fact, summary)
        result = self.call_llm(prompt)

        # Extract result and reason
        pass_fail = "fail"  # Default to fail
        reason = ""

        if "pass" in result.lower():
            pass_fail = "pass"

        reason_match = re.search(r'\[理由\]:(.*?)(?:\n|$)', result, re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            reason_match = re.search(r'理由:(.*?)(?:\n|$)', result, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()

        return {
            "result": pass_fail,
            "reason": reason
        }
        

    def get_laws_by_keyword_mapping(self, accident_facts: str, injuries: str, compensation_facts: str) -> List[str]:
        """
        Use keyword mapping to identify relevant laws for the case
        
        Args:
            accident_facts: The accident facts from user query
            injuries: The injuries section from user query
            compensation_facts: The compensation facts from user query
            
        Returns:
            List of law numbers that may be relevant
        """
        # Create keyword to law mapping based on reference function
        legal_mapping = {
            "184": ["未注意", "過失", "損害賠償", "侵害他人之權利"],
            "185": ["共同侵害", "共同行為", "數人侵害", "造意人"],
            "187": ["無行為能力", "限制行為能力", "法定代理人", "識別能力", "未成年"],
            "188": ["受僱人", "僱用人", "雇傭", "連帶賠償"],
            "191-2": ["汽車", "機車", "交通事故", "傷害", "損害"],
            "193": ["損失", "醫療費用", "工作", "損害", "身體", "薪資", "就醫", "傷"],
            "195": ["精神", "慰撫金", "痛苦", "名譽", "健康", "隱私", "貞操"],
            "213": ["回復原狀", "給付金錢", "損害發生"],
            "216": ["填補損害", "所失利益", "預期利益"],
            "217": ["被害人與有過失", "賠償金減輕", "重大損害原因"]
        }
        
        # Combine text for searching
        combined_text = f"{accident_facts} {injuries} {compensation_facts}"
        
        # Track identified laws
        identified_laws = set()
        
        # Search for keywords
        for law_number, keywords in legal_mapping.items():
            if any(keyword in combined_text for keyword in keywords):
                identified_laws.add(law_number)
        
        # Convert to sorted list
        return sorted(list(identified_laws))
    
    def check_law_content(self, accident_facts: str, injuries: str, law_number: str, law_content: str) -> Dict[str, str]:
        """
        Check if a specific law is applicable to the case
        
        Args:
            accident_facts: The accident facts from user query
            injuries: The injuries section from user query
            law_number: The law number to check
            law_content: The content of the law
            
        Returns:
            Dictionary with check result and reason
        """
        from ts_prompt_check import get_law_content_check_prompt
        
        prompt = get_law_content_check_prompt(accident_facts, injuries, law_number, law_content)
        result = self.call_llm(prompt)
        
        # Extract result and reason
        pass_fail = "fail"  # Default to fail
        reason = ""
        
        if "pass" in result.lower():
            pass_fail = "pass"
        
        reason_match = re.search(r'\[理由\]:(.*?)(?:\n|$)', result, re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            reason_match = re.search(r'理由:(.*?)(?:\n|$)', result, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()
        
        return {
            "result": pass_fail,
            "reason": reason
        }
    
    def check_compensation_part1(self, compensation_part1: str, injuries: str, compensation_facts: str, plaintiffs_info: str = "") -> Dict[str, str]:
        """
        Check if the generated compensation part 1 matches the injuries and compensation facts
        
        Args:
            compensation_part1: The generated compensation part 1
            injuries: The injuries section from user query
            compensation_facts: The compensation facts from user query
            plaintiffs_info: Information about plaintiffs extracted from input
            
        Returns:
            Dictionary with check result and reason
        """       
        prompt = get_compensation_part1_check_prompt(compensation_part1, injuries, compensation_facts, plaintiffs_info)
        result = self.call_llm(prompt)
        
        # Extract result and reason
        pass_fail = "fail"  # Default to fail
        reason = ""
        
        if "pass" in result.lower():
            pass_fail = "pass"
        
        reason_match = re.search(r'\[理由\]:(.*?)(?:\n|$)', result, re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            reason_match = re.search(r'理由:(.*?)(?:\n|$)', result, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()
        
        return {
            "result": pass_fail,
            "reason": reason
        }

    def check_amounts_in_summary(self, summary_section: str, compensation_sums: Dict[str, float]) -> Dict[str, str]:
        """
        Check if all amounts from compensation_sums appear in the summary section
        
        Args:
            summary_section: The summary section (綜上所陳 or 綜上所述)
            compensation_sums: Dictionary with compensation amounts
            
        Returns:
            Dictionary with check result and reason
        """
        # Remove all commas from the summary section to handle formatted numbers
        summary_without_commas = summary_section.replace(',', '')
        summary_without_commas = summary_without_commas.replace('，', '')
        
        # Track missing amounts
        missing_amounts = []
        
        # Check each amount
        for plaintiff, amount in compensation_sums.items():
            # Convert amount to integer string to match format in summary
            amount_str = str(int(amount))
            if amount_str not in summary_without_commas:
                missing_amounts.append(f"{amount_str}")
        
        # Return result
        if not missing_amounts:
            return {
                "result": "pass",
                "reason": "所有賠償金額都包含在總結中"
            }
        else:
            return {
                "result": "fail",
                "reason": f"總結中缺少以下賠償金額: {', '.join(missing_amounts)}"
            }
    
    def clean_facts_part(self, text: str) -> str:
        """
        Clean the facts part by removing excess text after max 2 newlines
        
        Args:
            text: Generated facts part text
            
        Returns:
            Cleaned facts part text
        """
        # Replace consecutive newlines with a single newline
        import re
        text = re.sub(r'\n+', '\n', text)
        
        # Find the first occurrence of "一、"
        start_idx = text.find("一、")
        if start_idx == -1:
            return text
        
        # Split the text after "一、" by newline
        remaining_text = text[start_idx:]
        parts = remaining_text.split('\n')
        
        # Keep only the first paragraph and at most one additional paragraph
        if len(parts) > 2:
            return '\n'.join(parts[:2])
        
        return remaining_text
    
    def clean_conclusion_part(self, text: str) -> str:
        """
        Clean the conclusion part by keeping only text before the first newline
        
        Args:
            text: Generated conclusion part text
            
        Returns:
            Cleaned conclusion part text
        """
        # Find the first occurrence of newline
        newline_idx = text.find('\n')
        if newline_idx == -1:
            return text
        
        # Return only the text before the first newline
        return text[:newline_idx]
    
    def remove_special_chars(self, text: str) -> str:
        """
        Remove specific special characters from text

        Args:
            text: Input text

        Returns:
            Text with specific special characters removed
        """
        import re
        # Remove only specific special characters like # and @
        return re.sub(r'[#@$%^&*~`\[\]]+', '', text)
    
    def clean_compensation_part(self, text: str) -> str:
        """
        Clean the compensation part by finding the last compensation item marker (（一）, （二）, etc.)
        and removing any content after a double newline following that marker.
        
        Args:
            text: Generated compensation part text
            
        Returns:
            Cleaned compensation part text
        """
        # Find all occurrences of compensation item markers
        import re
        item_markers = re.finditer(r'[一二三四五六七八九十]+、', text, re.MULTILINE)
        
        # Get the position of the last marker
        last_marker_pos = -1
        for match in item_markers:
            last_marker_pos = match.start()
        
        # If no markers found, return the original text
        if last_marker_pos == -1:
            return text
        
        # Find double newline after the last marker
        double_newline_pos = text.find("\n\n", last_marker_pos)
        
        # If no double newline found, return the original text
        if double_newline_pos == -1:
            return text
        
        # Return text up to the double newline
        return text[:double_newline_pos].strip()
        
    def generate_facts(self, accident_facts: str, reference_fact_text: str) -> str:
        """
        Generate facts part using LLM
        
        Args:
            accident_facts: The accident facts from user query
            reference_fact_text: Reference fact text
            
        Returns:
            Generated facts part
        """
        prompt = get_facts_prompt(accident_facts, reference_fact_text)
        return self.call_llm(prompt)
        
    def generate_compensation_part1(self, injuries: str, compensation_facts: str, include_conclusion: bool, average_compensation: float, case_type: str, plaintiffs_info: str = "") -> str:
        """
        Generate compensation part 1 using LLM
        
        Args:
        injuries: Injuries description
        compensation_facts: Compensation facts
        include_conclusion: Whether to include average compensation info
        average_compensation: Average compensation amount
        case_type: The case type to determine template
        plaintiffs_info: Information about plaintiffs extracted from input
            
        Returns:
            Generated compensation part 1
        """
        # Determine if case involves multiple plaintiffs based on case_type
        is_multiple_plaintiffs = any(x in case_type for x in ["數名原告", "原被告皆數名"])

        if is_multiple_plaintiffs:
            # Use multiple plaintiffs template
            if include_conclusion and average_compensation > 0:
                prompt = get_compensation_prompt_part1_multiple_plaintiffs(injuries, compensation_facts, average_compensation, plaintiffs_info)
            else:
                prompt = get_compensation_prompt_part1_multiple_plaintiffs(injuries, compensation_facts, plaintiffs_info=plaintiffs_info)
        else:
            # Use single plaintiff template
            if include_conclusion and average_compensation > 0:
                prompt = get_compensation_prompt_part1_single_plaintiff(injuries, compensation_facts, average_compensation, plaintiffs_info)
            else:
                prompt = get_compensation_prompt_part1_single_plaintiff(injuries, compensation_facts, plaintiffs_info=plaintiffs_info)

        return self.call_llm(prompt)
        
    def generate_compensation_part2(self, compensation_part1: str, plaintiffs_info: str = "") -> str:
        """
        Generate compensation part 2 (calculation tags) using LLM
        
        Args:
            compensation_part1: The compensation part 1 text
            plaintiffs_info: Information about plaintiffs extracted from input
        Returns:
            Generated calculation tags
        """
        prompt = get_compensation_prompt_part2(compensation_part1, plaintiffs_info)
        return self.call_llm(prompt)
        
    def generate_compensation_part3(self, compensation_part1: str, summary_format: str, plaintiffs_info: str = "") -> str:
        """
        Generate compensation part 3 (conclusion) using LLM
        
        Args:
            compensation_part1: The compensation part 1 text
            summary_format: The summary format string
            plaintiffs_info: Information about plaintiffs extracted from input
        Returns:
            Generated conclusion part
        """
        prompt = get_compensation_prompt_part3(compensation_part1, summary_format, plaintiffs_info)
        return self.call_llm(prompt)
        
    
    # Add this method to the RetrievalSystem class in ts_retrieval_system.py
    def check_calculation_tags(self, compensation_part1: str, compensation_part2: str) -> Dict[str, str]:
        """
        Check if the generated calculation tags are valid and match the compensation items
        
        Args:
            compensation_part1: The compensation items text
            compensation_part2: The generated calculation tags
            
        Returns:
            Dictionary with check result and reason
        """
        prompt = get_calculation_tags_check_prompt(compensation_part1, compensation_part2)
        result = self.call_llm(prompt)
        
        # Extract result and reason
        pass_fail = "fail"  # Default to fail
        reason = ""
        
        if "pass" in result.lower():
            pass_fail = "pass"
        
        reason_match = re.search(r'\[理由\]:(.*?)(?:\n|$)', result, re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            reason_match = re.search(r'理由:(.*?)(?:\n|$)', result, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()
        
        return {
            "result": pass_fail,
            "reason": reason
        }