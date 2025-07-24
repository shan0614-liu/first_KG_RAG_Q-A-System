from QuestionAnalyzer import QuestionPreprocessor, IntentAnalyzer
from KGQuery import CypherGenerator, KGQueryExecutor
from AnswerGenerator import AnswerGenerator
import re

class ScholarQASystem:
    def __init__(self):
        self.preprocessor = QuestionPreprocessor()
        self.intent_analyzer = IntentAnalyzer()
        self.cypher_generator = CypherGenerator()
        self.kg_executor = KGQueryExecutor()
        self.answer_generator = AnswerGenerator()

    def answer(self, question: str) -> str:
        processed_question = self.preprocessor.process(question)
        if not processed_question:
            return "请输入有效的问题。"

        # 多意图分析
        analysis = self.intent_analyzer.analyze(processed_question)
        print(f"意图识别结果: {analysis}")

        # 检查是否有有效的实体和意图
        if not analysis["entities"] or not analysis["intents"]:
            # 降级处理
            author_pattern = re.compile(r'([\u4e00-\u9fa5]+)学者|与([\u4e00-\u9fa5]+)合作')
            match = author_pattern.search(processed_question)
            if match:
                author_name = next((g for g in match.groups() if g), None)
                if author_name:
                    analysis = {
                        "entities": [{"name": author_name, "type": "Author"}],
                        "intents": [{"entity": author_name, "intent": "查询合作学者"}]
                    }
                    print(f"降级意图识别: {analysis}")
                else:
                    return "未能理解问题，请尝试重新表述。"
            else:
                return "未能理解问题，请尝试重新表述。"

        # 为多个意图生成Cypher查询
        cyphers = self.cypher_generator.generate(analysis["entities"], analysis["intents"], processed_question)
        print(f"生成的Cypher查询: {[c['cypher'] for c in cyphers]}")

        if not cyphers:
            return "无法生成查询，请尝试其他问题。"

        # 执行多个查询
        kg_results = self.kg_executor.execute(cyphers)
        print(f"知识图谱查询结果: {kg_results}")

        # 生成综合回答
        return self.answer_generator.generate(processed_question, kg_results)

if __name__ == "__main__":
    qa_system = ScholarQASystem()
    print("学者知识问答系统已启动（输入'退出'结束）")
    while True:
        user_question = input("请输入问题：")
        if user_question == "退出":
            break
        answer = qa_system.answer(user_question)
        print(f"回答：\n{answer}\n")