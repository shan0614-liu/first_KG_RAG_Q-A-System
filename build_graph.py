# 导入必要的库：os用于文件路径处理，json用于解析JSON数据，py2neo用于操作Neo4j图数据库
import os
import json
from py2neo import Graph, Node, Relationship

# 定义ScholarGraph类，封装学术知识图谱的构建逻辑
class ScholarGraph:
    # 类的初始化方法，用于设置数据路径、连接数据库并清空现有数据
    def __init__(self,clear_all):
        # 获取当前文件的绝对路径，并截取到上一级目录（用于拼接数据文件路径）
        cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        # 拼接数据集路径：当前目录下的data文件夹中的data_test.json
        self.data_path = os.path.join(cur_dir, 'data/data.json')
        # 连接Neo4j数据库（地址、用户名、密码固定）
        self.g = Graph("http://localhost:7474", auth=("neo4j", "liuwdsrL123!"))
        # 清空数据库中所有现有节点和关系，确保每次构建是全新图谱
        if clear_all:
            self.g.delete_all()
            print("已清空原有图谱！")

    # 核心方法：创建知识图谱的主逻辑
    def create_graph(self):
        # 打开并读取JSON数据集文件
        with open(self.data_path, 'r', encoding='utf-8') as f:
            # 将JSON数据解析为Python列表（每一项是一篇论文的信息）
            articles = json.load(f)

        # 遍历每篇论文，创建节点和关系
        for article in articles:
            # 创建Article（论文）节点，包含论文的核心属性
            article_node = Node(
                'Article',  # 节点标签为"Article"
                id=article['id'],  # 论文唯一标识
                title=article['title'],  # 论文标题
                date=str(article['date_parts'][0][0]),  # 发表年份（转换为字符串）
                keywords=article['keywords'],  # 关键词列表直接以列表形式存储，保留列表的结构化信息，后续可以直接通过 “关键词包含某词” 进行精确查询，保留查询灵活性
                abstract=article['abstract'],  # 论文摘要
                language=article['language']  # 论文语言（如en、zh）
            )
            # 将artical_node节点合并到数据库（根据属性id去重，避免重复创建）
            self.g.merge(article_node, 'Article', 'id')

            # 创建Journal（期刊）节点，并建立论文与期刊的关系
            journal_node = Node(
                'Journal',  # 节点标签为"Journal"
                name=article['container_title'],  # 期刊名称
                issn_isbn=article['ISSN_ISBN'],  # 期刊的ISSN/ISBN编号
                impact_factor=article.get('impact_factor')  # 期刊影响因子（可能为null）
            )
            # 将期刊节点合并到数据库（根据name去重）
            self.g.merge(journal_node, 'Journal', 'name')
            # 创建"BE_PUBLISHED_IN"（刊载于）关系：论文 -> 期刊
            rel = Relationship(article_node, 'BE_PUBLISHED_IN', journal_node)
            self.g.merge(rel)  # 合并关系（避免重复）

            # 处理作者节点及作者与论文、作者之间的关系
            authors = []  # 存储当前论文的所有作者节点，用于后续创建合作关系
            # 遍历论文的作者列表
            for author in article['author']:
                # 提取作者的姓、名、中文名（若有）
                family = author.get('family', '')  # 姓（如"Chen"）
                given = author.get('given', '')  # 名（如"Gang"）
                chinese_name = author.get('chinese_name', '')  # 中文名（如"陈钢"）
                # 从论文中提取二级学科信息（取第一个学科的缩写）
                discipline = ""
                if 'class_en' in article and 'Secondary disciplines' in article['class_en']:
                    disciplines = article['class_en']['Secondary disciplines']
                    if disciplines:
                        # 取第一个学科的前3个字母作为缩写（如"Vibration Engineering" → "Vib"）
                        discipline = disciplines[0].split()[0][:3].upper()

                # 若作者姓名不为空（避免无效数据）
                if family or given:
                    # 创建Author（作者）节点
                    author_node = Node(
                        'Author',  # 节点标签为"Author"
                        english_name=f"{family} {given}".strip(),  # 英文名（姓+名）
                        chinese_name=chinese_name, # 中文名（可为空）
                        unique_id = f"{family}{given}{discipline}"# 唯一标识：姓名 + 研究领域
                    )

                    # 将作者节点合并到数据库（根据english_name去重）
                    self.g.merge(author_node, 'Author', 'unique_id')
                    # 将作者节点加入列表，用于后续创建合作关系
                    authors.append(author_node)

                    # 创建"PUBLISH"（发表）关系：作者 -> 论文
                    rel = Relationship(author_node, 'PUBLISH', article_node)
                    self.g.merge(rel)  # 合并关系

            # 创建作者之间的"COLLABORATE"（合作）关系
            # 双重循环遍历作者列表，为每对不同作者创建合作关系
            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    # 作者i与作者j之间建立合作关系
                    rel = Relationship(authors[i], 'COLLABORATE', authors[j])
                    self.g.merge(rel)  # 合并关系（同一对作者只保留一条）

            # 处理二级学科分类：创建Discipline节点及论文与学科的关系
            self.create_classification(
                article_node,  # 关联的论文节点
                article,  # 论文数据
                'class_en', 'Secondary disciplines',  # 英文分类字段（大类+子字段）
                'class_zh', '二级学科',  # 中文分类字段（大类+子字段）
                'Discipline',  # 节点标签
                'BELONG_TO'  # 关系类型（属于）
            )

            # 处理研究主题：创建Topic节点及论文与主题的关系
            self.create_classification(
                article_node,
                article,
                'class_en', 'Research direction clusters',  # 英文研究主题字段
                'class_zh', '研究主题',  # 中文研究主题字段
                'Topic',  # 节点标签
                'INVOLVE'  # 关系类型（涉及）
            )

            # 处理方法技术：创建Method节点及论文与方法的关系
            self.create_classification(
                article_node,
                article,
                'class_en', 'Methods and technologies',  # 英文方法技术字段
                'class_zh', '方法技术',  # 中文方法技术字段
                'Method',  # 节点标签
                'USE'  # 关系类型（使用）
            )

            # 处理应用场景：创建Scenario节点及论文与场景的关系
            self.create_classification(
                article_node,
                article,
                'class_en', 'Application scenarios',  # 英文应用场景字段
                'class_zh', '应用场景',  # 中文应用场景字段
                'Scenario',  # 节点标签
                'APPLY_TO'  # 关系类型（应用于）
            )

    # 辅助方法：创建分类节点（如学科、主题等）及与论文的关系
    def create_classification(self, article_node, article,
                              en_key, en_subkey, zh_key, zh_subkey,
                              node_type, rel_type):
        """
        :param article_node: 论文节点（起点）
        :param article: 论文原始数据
        :param en_key: 英文分类的父字段（如"class_en"）
        :param en_subkey: 英文分类的子字段（如"Secondary disciplines"）
        :param zh_key: 中文分类的父字段（如"class_zh"）
        :param zh_subkey: 中文分类的子字段（如"二级学科"）
        :param node_type: 分类节点的标签（如"Discipline"）
        :param rel_type: 论文与分类节点的关系类型（如"BELONG_TO"）
        """
        # 检查数据中是否包含英文分类字段及子字段
        if en_key in article and en_subkey in article[en_key]:
            # 提取英文分类项列表（如["Vibration Engineering", ...]）
            en_items = article[en_key][en_subkey]
            # 提取中文分类项列表（若存在，否则为空列表）
            zh_items = article[zh_key][zh_subkey] if (zh_key in article and zh_subkey in article[zh_key]) else []

            # 遍历每个英文分类项，创建对应的分类节点
            for i, item_en in enumerate(en_items):
                # 匹配对应的中文分类项（若索引存在则取对应值，否则为空）
                item_zh = zh_items[i] if i < len(zh_items) else ""

                # 创建分类节点（包含中英文名称）
                node = Node(
                    node_type,  # 节点标签（如"Discipline"）
                    english_name=item_en,  # 英文名称
                    chinese_name=item_zh  # 中文名称
                )
                # 将分类节点合并到数据库（根据english_name去重）
                self.g.merge(node, node_type, 'english_name')

                # 创建论文与分类节点的关系（如论文->属于->学科）
                rel = Relationship(article_node, rel_type, node)
                self.g.merge(rel)  # 合并关系


# 主程序入口：当脚本直接运行时执行
if __name__ == '__main__':
    # 创建ScholarGraph实例（初始化数据库连接并清空数据）
    handler = ScholarGraph(True)
    # 调用create_graph方法构建知识图谱
    handler.create_graph()
    # 输出构建完成的提示信息
    print("知识图谱构建完成！")