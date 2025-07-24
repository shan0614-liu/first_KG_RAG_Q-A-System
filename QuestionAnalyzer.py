import json
import re
import openai
from typing import List, Dict

# 配置类
class Config:
    NEO4J_URI = "http://localhost:7474"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "liuwdsrL123!"

    DEEPSEEK_API_KEY = "API密钥"
    DEEPSEEK_MODEL = "deepseek-chat"
    API_TIMEOUT = 60
    API_BASE_URL = "https://api.deepseek.com"

# 初始化 openai 客户端
client = openai.OpenAI(
    api_key=Config.DEEPSEEK_API_KEY,
    base_url=Config.API_BASE_URL,
    timeout=Config.API_TIMEOUT
)

# 问题预处理类
class QuestionPreprocessor:
    @staticmethod
    def process(question: str) -> str:
        question = re.sub(r'\s+', ' ', question).strip() #\s+：将问句中任意长度的空白字符转换为单个空白字符；.strip()去除文本的开头和结尾空格
        return question

# 意图分析类
class IntentAnalyzer:
    def __init__(self):
        self.client = client
        self.system_prompt = """
        你是一个专业的学术问题解析器，请严格依据以下实体、属性和关系定义，分析用户问题，提取关键实体及其类型和多个查询意图。

        实体类型及属性说明
        Author（学者）：属性包含英文名（family+given）、中文名（chinese_name） 
        Article（论文）：属性有标题（title）、ID（id）、发表年份（date_parts）、关键词（keywords）、摘要（abstract）、语言（language） 
        Journal（期刊）：属性为名称（container_title）、ISSN/ISBN、影响因子（impact_factor） 
        Discipline（二级学科）：属性是英文名称（class_en.Secondary disciplines）、中文名称（class_zh.二级学科） 
        Topic（研究主题）：属性为英文名称（class_en.Research direction clusters）、中文名称（class_zh.研究主题） 
        Method（方法技术）：属性是英文名称（class_en.Methods and technologies）、中文名称（class_zh.方法技术） 
        Scenario（应用场景）：属性为英文名称（class_en.Application scenarios）、中文名称（class_zh.应用场景） 

        关系类型及连接实体说明
        PUBLISH（发表）：连接实体为 Author → Article ，表示学者发表论文的关系 
        COLLABORATE（合作）：连接实体为 Author → Author ，代表学者之间合作发表论文的关系 
        BE_PUBLISHED_IN（刊载于）：连接实体为 Article → Journal ，即论文刊载于某期刊的关系 
        BELONG_TO（属于）：连接实体为 Article → Discipline ，说明论文所属二级学科的关系 
        INVOLVE（涉及）：连接实体为 Article → Topic ，表示论文涉及某研究主题的关系 
        USE（使用）：连接实体为 Article → Method ，代表论文使用某方法技术的关系 
        APPLY_TO（应用于）：连接实体为 Article → Scenario ，说明论文应用于某应用场景的关系 

        意图可选方向
        学者（Author）相关：论文列表（查询论文信息，基于 PUBLISH 关系 ）、合作学者（查询有合作关系的其他学者，基于 COLLABORATE 关系 ）、研究领域（查询二级学科（研究领域），可通过 PUBLISH → BELONG_TO 关系推导 ）、发表期刊（查询发表的期刊，通过 PUBLISH → BE_PUBLISHED_IN 关系推导 ） 
        论文（Article）相关：作者列表（查询论文的作者，基于 PUBLISH 关系反向推导 ）、发表时间（提取论文的发表时间）、关键词（提取论文的关键词）、所属领域（查询论文所属二级学科）、涉及主题（查询论文涉及的研究主题，基于 INVOLVE 关系 ）、使用方法（查询论文使用的方法技术，基于 USE 关系 ）、应用场景（查询论文应用的场景，基于 APPLY_TO 关系 ） 
        期刊（Journal）相关：发表论文（查询期刊上刊载的论文，基于 BE_PUBLISHED_IN 关系反向推导 ）、影响因子（提取期刊的影响因子） 
        二级学科（Discipline）相关：相关论文（查询属于该二级学科的论文，基于 BELONG_TO 关系反向推导 ）、研究学者（查询发表过该二级学科相关论文的学者，通过 BELONG_TO → PUBLISH 关系推导 ） 
        研究主题（Topic）相关：相关论文（查询涉及该研究主题的论文，基于 INVOLVE 关系反向推导 ）、研究学者（查询发表过该研究主题相关论文的学者，通过 INVOLVE → PUBLISH 关系推导 ） 
        方法技术（Method）相关：相关论文（查询使用该方法技术的论文，基于 USE 关系反向推导 ）、应用学者（查询发表过使用该方法技术论文的学者，通过 USE → PUBLISH 关系推导 ） 
        应用场景（Scenario）相关：相关论文（查询应用于该场景的论文，基于 APPLY_TO 关系反向推导 ）、应用学者（查询发表过应用于该场景论文的学者，通过 APPLY_TO → PUBLISH 关系推导 ） 

        特别要求：
        1. 实体名称必须严格保留原始格式，包括括号、标点等
        2. 一个问题可能包含多个意图，请识别出所有可能的意图
        3. 返回JSON格式，包含entities数组和intents数组（注意是intents复数形式）
        4. 每个意图需明确对应实体，格式示例: {"entities": [{"name": "陈钢", "type": "Author"}, {"name": "人工智能", "type": "Topic"}], "intents": [{"entity": "陈钢", "intent": "查询学者的论文列表"}, {"entity": "人工智能", "intent": "查询相关论文"}]}
        """

    def analyze(self, question: str) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model=Config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ],
                timeout=Config.API_TIMEOUT
            )
            result_text = response.choices[0].message.content.strip()

            # 清理可能的Markdown格式
            if result_text.startswith("```json") and result_text.endswith("```"):
                result_text = result_text[len("```json"):-len("```")].strip()

            try:
                result = json.loads(result_text)
                # 确保返回格式正确
                return {
                    "entities": result.get("entities", []),
                    "intents": result.get("intents", [])
                }
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {result_text}")
                print(f"错误详情: {str(e)}")
                # 降级处理
                entities = []
                intents = []
                author_match = re.search(r'([\u4e00-\u9fa5]+)学者', question)
                if author_match:
                    author_name = author_match.group(1)
                    entities = [{"name": author_name, "type": "Author"}]
                    intents = [{"entity": author_name, "intent": "查询学者的论文列表"}]
                return {"entities": entities, "intents": intents}
            except Exception as e:
                print(f"解析结果失败: {str(e)}")
                return {"entities": [], "intents": []}
        except Exception as e:
            print(f"意图识别失败：{str(e)}")
            return {"entities": [], "intents": []}
