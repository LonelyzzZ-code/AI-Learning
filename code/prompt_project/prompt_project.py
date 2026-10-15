import os
from openai import OpenAI

client = OpenAI(
    api_key = os.environ["ZHIPU_API_KEY"],
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

lizis = [
        {"role": "system", "content": """把用户的问题改写成搜索关键词。
            规则：只输出 2~4 个关键词，用空格分隔；
            不要回答问题，不要解释，不要编号，不要加"关键词："之类的前缀。"""},
        {"role": "system", "content": "把用户问题改写成搜索关键词。"},
        {"role": "user", "content": "那篇讲数据库索引的文章叫啥"},
        {"role": "assistant", "content": "数据库 索引"},
        {"role": "user", "content": "怎么用redis做缓存"},
        {"role": "assistant", "content": "Redis 缓存"},
    ]

question = ["那个讲数据库索引的笔记是哪篇", 
            "咋用redis加速", 
            "vue组件怎么传值",
            "python咋读excel文件", 
            "网页加载慢咋排查"]

def rewrite(question: str) -> str: 
    response = client.chat.completions.create(
        model = "glm-4-flash",
        messages = lizis + [{"role": "user", "content": question}],
        temperature = 0.1,
        max_tokens = 32 
    )
    resp = response.choices[0].message.content
    print(f"AI回答的内容是：{resp}")

for q in question:
    rewrite(q)
