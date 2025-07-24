import json
from typing import List, Dict
from QuestionAnalyzer import Config, client  # 导入配置和客户端


class AnswerGenerator:
    def __init__(self):
        self.client = client

    def generate(self, question: str, kg_results: List[Dict]) -> str:
        if not kg_results:
            return "未查询到相关信息，请尝试其他问题。"

        # 格式化多个查询结果
        formatted_results = []
        for result in kg_results:
            if result["results"]:  # 只包含有结果的查询
                formatted_results.append({
                    "intent": result["intent"],
                    "entity": result["entity"]["name"],
                    "results": result["results"]
                })

        if not formatted_results:
            return "未查询到相关信息，请尝试其他问题。"

        formatted_json = json.dumps(formatted_results, ensure_ascii=False, indent=2)

        system_prompt = """
        请根据以下多个知识图谱查询结果（JSON格式），用自然语言回答用户问题。
        要求：
        1. 每个意图的结果单独成段，先说明意图，再列出结果
        2. 结果为合作学者时，直接列出姓名（含中英文），如"1. 刘丹（Liu Dan）"
        3. 必须严格基于查询结果，结果非空时直接列出（如论文标题、年份）
        4. 严格基于查询结果，不添加额外内容
        5. 用中文简洁回答，无需解释
        """

        try:
            response = self.client.chat.completions.create(
                model=Config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"查询结果：\n{formatted_json}\n\n用户问题：{question}"}
                ],
                timeout=Config.API_TIMEOUT
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"答案生成失败：{str(e)}")
            # 降级处理：直接格式化输出
            answer_parts = []
            for result in formatted_results:
                answer_parts.append(f"关于{result['entity']}的{result['intent']}：")
                for i, item in enumerate(result['results'], 1):
                    item_str = ", ".join([f"{k}：{v}" for k, v in item.items()])
                    answer_parts.append(f"{i}. {item_str}")
                answer_parts.append("")  # 空行分隔不同意图

            return "\n".join(answer_parts)