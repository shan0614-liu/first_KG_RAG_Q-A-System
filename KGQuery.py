import re
from py2neo import Graph, DatabaseError
from typing import List, Dict, Optional
from QuestionAnalyzer import Config  # 导入配置类

# Cypher 查询生成类
class CypherGenerator:
    def __init__(self):
        # 定义学术领域的问句疑问词
        self.collab_qwds = ['合作', '协作', '共同研究', '联合发表', '合著', '合作者', '合作伙伴']
        self.citation_qwds = ['引用', '被引', '参考文献', '参考', '引文', '引用量']
        self.impact_qwds = ['影响', '作用', '贡献', '重要性', '意义', '价值', '影响力']
        self.compare_qwds = ['比较', '对比', '相比', '差异', '区别', '不同点', '异同']
        self.paper_qwds = ['论文', '文章', '发表', '成果', '出版物', '文献', '著作']
        self.author_qwds = ['作者', '学者', '研究者', '教授', '专家', '科学家', '撰稿人']
        self.journal_qwds = ['期刊', '杂志', '学报', '会议', '出版物', '刊载', '发表刊物']
        self.discipline_qwds = ['学科', '领域', '专业', '方向', '分支', '二级学科', '研究领域']
        self.method_qwds = ['方法', '技术', '算法', '模型', '框架', '方法论', '分析技术', '计算方法']
        self.scenario_qwds = ['应用', '场景', '实践', '实施', '使用', '应用领域', '使用场景']
        self.topic_qwds = ['主题', '研究方向', '研究主题', '研究重点', '研究内容', '研究课题']
        self.keyword_qwds = ['关键词', '术语', '标签', '核心词汇', '关键术语']
        self.time_qwds = ['时间', '年份', '年代', '何时', '发表时间', '出版时间', '日期']
        self.factor_qwds = ['影响因子', 'IF', 'JIF', '期刊影响因子', 'citation impact', '期刊评价']
        self.abstract_qwds = ['摘要', '概要', '内容摘要', '主要内容', 'abstract', '简介', '概述', '总结', '内容简述']

    def check_words(self, wds, sent):
        """检查特征词是否在意图中出现"""
        for wd in wds:
            if wd in sent:
                return True
        return False

    def generate_for_intent(self, entity: Dict, intent: str, question: str) -> Optional[str]:
        """为单个意图生成Cypher查询"""
        SUPPORTED_ENTITY_TYPES = [
            "Author", "Article", "Topic", "Journal",
            "Discipline", "Method", "Scenario"
        ]

        if entity["type"] not in SUPPORTED_ENTITY_TYPES:
            return None

        entity_name = entity["name"]
        entity_type = entity["type"]

        # 使用问句分类机制增强意图识别
        if entity_type == "Author":
            # 研究主题分析
            if self.check_words(self.topic_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:PUBLISH]->(p:Article)-[:INVOLVE]->(d:Topic)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN p.date AS 年份, count(p) AS 发表数量
                           ORDER BY p.date
                           """
            # 研究领域查询（二级学科）
            elif self.check_words(self.discipline_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:PUBLISH]->(p:Article)-[:BELONG_TO]->(d:Discipline)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN DISTINCT d.chinese_name AS 二级学科, d.english_name AS 英文领域
                           """
            # 发表期刊查询
            elif self.check_words(self.journal_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:PUBLISH]->(p:Article)-[:BE_PUBLISHED_IN]->(j:Journal)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN DISTINCT j.name AS 期刊名称, j.impact_factor AS 影响因子
                           ORDER BY j.impact_factor DESC
                           """
            # 研究方法查询
            elif self.check_words(self.method_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:PUBLISH]->(p:Article)-[:USE]->(m:Method)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN DISTINCT m.chinese_name AS 方法技术
                           """
            # 应用场景查询
            elif self.check_words(self.scenario_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:PUBLISH]->(p:Article)-[:APPLY_TO]->(s:Scenario)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN DISTINCT s.chinese_name AS 应用场景
                           """
            # 论文列表查询
            elif self.check_words(self.paper_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:PUBLISH]->(p:Article)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN p.title AS 论文标题, p.date AS 发表年份, p.container_title AS 期刊名称
                           ORDER BY p.date DESC
                           """
            # 合作学者查询
            elif self.check_words(self.collab_qwds, intent):
                return f"""
                           MATCH (a:Author)-[:COLLABORATE]-(c:Author)
                           WHERE a.chinese_name = "{entity_name}" OR a.english_name = "{entity_name}"
                           RETURN c.chinese_name AS 中文名, c.english_name AS 英文名
                           """

        elif entity_type == "Article":
            # 摘要查询（根据论文属性）
            if self.check_words(self.abstract_qwds, intent):  # 正则表达式(?i)忽略大小写，.*匹配任意数量的任意字符
                return f"""
                           MATCH (p:Article)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*" 
                           RETURN p.title AS 论文标题, p.abstract AS 摘要
                           LIMIT 1
                           """
            # 作者查询
            elif self.check_words(self.author_qwds, intent):
                return f"""
                           MATCH (p:Article)<-[:PUBLISH]-(a:Author)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN a.chinese_name AS 中文名, a.english_name AS 英文名
                           """
            # 发表期刊查询
            elif self.check_words(self.journal_qwds, intent):
                return f"""
                           MATCH (p:Article)-[:BE_PUBLISHED_IN]->(j:Journal)
                           WHERE p.title CONTAINS "{entity_name}"
                           RETURN j.name AS 期刊名称, j.impact_factor AS 影响因子, p.date AS 发表年份
                           """
            # 发表时间查询
            elif self.check_words(self.time_qwds, intent):
                return f"""
                           MATCH (p:Article)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.date AS 发表年份
                           """
            # 关键词查询（根据论文属性）
            elif self.check_words(self.keyword_qwds, intent):
                return f"""
                           MATCH (p:Article)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.keywords AS 关键词
                           """
            # 研究领域查询（二级学科）
            elif self.check_words(self.discipline_qwds, intent):
                return f"""
                           MATCH (p:Article)-[:BELONG_TO]->(d:Discipline)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN d.chinese_name AS 二级学科
                           """
            # 研究主题查询（根据关系定义）
            elif self.check_words(self.topic_qwds, intent):
                return f"""
                           MATCH (p:Article)-[:INVOLVE]->(t:Topic)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN t.chinese_name AS 研究主题
                           """
            # 方法技术查询（根据关系定义）
            elif self.check_words(self.method_qwds, intent):
                return f"""
                           MATCH (p:Article)-[:USE]->(m:Method)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN m.chinese_name AS 方法技术
                           """
            # 应用场景查询（根据关系定义）
            elif self.check_words(self.scenario_qwds, intent):
                return f"""
                           MATCH (p:Article)-[:APPLY_TO]->(s:Scenario)
                           WHERE p.title =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN s.chinese_name AS 应用场景
                           """

        elif entity_type == "Topic":
            # 相关论文查询
            if self.check_words(self.paper_qwds, intent):
                return f"""
                           MATCH (t:Topic)<-[:INVOLVE]-(p:Article)
                           WHERE t.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR t.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.title AS 论文标题, p.date AS 发表年份
                           ORDER BY p.date DESC
                           """
            # 相关学者查询
            elif self.check_words(self.author_qwds, intent):
                return f"""
                           MATCH (t:Topic)<-[:INVOLVE]-(p:Article)<-[:PUBLISH]-(a:Author)
                           WHERE t.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR t.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN DISTINCT a.chinese_name AS 中文名, a.english_name AS 英文名
                           """

        elif entity_type == "Journal":
            # 发表论文查询
            if self.check_words(self.paper_qwds, intent):
                return f"""
                           MATCH (j:Journal)<-[:BE_PUBLISHED_IN]-(p:Article)
                           WHERE j.name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.title AS 论文标题, p.date AS 发表年份
                           ORDER BY p.date DESC
                           """
            # 影响因子查询（根据期刊属性）
            elif self.check_words(self.factor_qwds, intent):
                return f"""
                           MATCH (j:Journal)
                           WHERE j.name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN j.impact_factor AS 影响因子
                           """

        elif entity_type == "Discipline":
            # 相关论文查询
            if self.check_words(self.paper_qwds, intent):
                return f"""
                           MATCH (d:Discipline)<-[:BELONG_TO]-(p:Article)
                           WHERE d.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR d.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.title AS 论文标题, p.date AS 发表年份
                           ORDER BY p.date DESC
                           """
            # 相关学者查询
            elif self.check_words(self.author_qwds, intent):
                return f"""
                           MATCH (d:Discipline)<-[:BELONG_TO]-(p:Article)<-[:PUBLISH]-(a:Author)
                           WHERE d.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR d.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN DISTINCT a.chinese_name AS 中文名, a.english_name AS 英文名
                           """

        elif entity_type == "Method":
            # 应用学者查询
            if self.check_words(self.author_qwds, intent):
                return f"""
                           MATCH (m:Method)<-[:USE]-(p:Article)<-[:PUBLISH]-(a:Author)
                           WHERE m.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR m.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN DISTINCT a.chinese_name AS 中文名, a.english_name AS 英文名
                           """
            # 相关论文查询
            elif self.check_words(self.paper_qwds, intent):
                return f"""
                           MATCH (m:Method)<-[:USE]-(p:Article)
                           WHERE m.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR m.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.title AS 论文标题, p.date AS 发表年份
                           ORDER BY p.date DESC
                           """

        elif entity_type == "Scenario":
            # 相关论文查询
            if self.check_words(self.paper_qwds, intent):
                return f"""
                           MATCH (s:Scenario)<-[:APPLY_TO]-(p:Article)
                           WHERE s.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR s.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN p.title AS 论文标题, p.date AS 发表年份
                           ORDER BY p.date DESC
                           """
            # 应用学者查询
            elif self.check_words(self.author_qwds, intent):
                return f"""
                           MATCH (s:Scenario)<-[:APPLY_TO]-(p:Article)<-[:PUBLISH]-(a:Author)
                           WHERE s.chinese_name =~ "(?i).*{re.escape(entity_name)}.*" OR s.english_name =~ "(?i).*{re.escape(entity_name)}.*"
                           RETURN DISTINCT a.chinese_name AS 中文名, a.english_name AS 英文名
                           """

        return None

    def generate(self, entities: List[Dict], intents: List[Dict], question: str) -> List[Dict]:
        """为多个意图生成多个Cypher查询"""
        results = []
        entity_map = {e["name"]: e for e in entities}

        for intent_info in intents:
            entity_name = intent_info.get("entity")
            intent_text = intent_info.get("intent")

            if not entity_name or not intent_text:
                continue

            entity = entity_map.get(entity_name)
            if not entity:
                continue

            cypher = self.generate_for_intent(entity, intent_text, question)
            if cypher:
                results.append({
                    "entity": entity,
                    "intent": intent_text,
                    "cypher": cypher
                })

        return results


# 知识图谱查询执行器
class KGQueryExecutor:
    def __init__(self):
        self.graph = Graph(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        )

    def execute(self, cyphers: List[Dict]) -> List[Dict]:
        """执行多个Cypher查询并返回结果"""
        results = []

        for query_info in cyphers:
            try:
                cypher = query_info["cypher"]
                result = self.graph.run(cypher).data()
                results.append({
                    "entity": query_info["entity"],
                    "intent": query_info["intent"],
                    "results": result
                })
            except DatabaseError as e:
                print(f"Cypher执行错误：{str(e)}，查询：{query_info['cypher']}")

        return results
