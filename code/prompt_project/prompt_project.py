import os
from openai import OpenAI

client = OpenAI(
    api_key = os.environ["ZHIPU_API_KEY"],
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

from prompts import REWRITE_MESSAGES_V1

question = ["那个讲数据库索引的笔记是哪篇",
            "咋用redis加速",
            "vue组件怎么传值",
            "python咋读excel文件",
            "网页加载慢咋排查"]

def rewrite(question: str) -> str:
    response = client.chat.completions.create(
        model = "glm-4-flash",
        messages = REWRITE_MESSAGES_V1 + [{"role": "user", "content": question}],
        temperature = 0.1,
        max_tokens = 32 
    )
    resp = response.choices[0].message.content
    print(f"AI回答的内容是：{resp}")

for q in question:
    rewrite(q)
