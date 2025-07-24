build_graph.py是构建知识图谱的文件
chatbot_graph.py是问答系统主函数
QuestionAnalyzer.py是问题预处理与意图识别部分
KGQuery.py是构建Cypher查询与知识图谱检索部分
AnswerGenerator.py是调用大语言模型，生成结果部分

运行步骤：
1.先在浏览器连接打开neo4j，运行bulid_graph.py，生成知识图谱
（数据位置为data/data.json，数据量较大，运行时间较长，若想节约时间，可用data/data_tast.json，把bulid_graph中第13行文件路径由data/data.json改为data/data_tast.json即可）
2.再运行chatbot_graph.py进行提问，输入“退出”，即可退出程序。
