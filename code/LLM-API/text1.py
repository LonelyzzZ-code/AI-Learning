import os
from openai import OpenAI

client = OpenAI(
    api_key =  os.environ["ZHIPU_API_KEY"],
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

messages = []
questions = [
    "我叫小明，我最喜欢的数字是 42，请记住。",
    "我最喜欢吃的水果是榴莲，也请记住。",
    "我刚才说最喜欢的数字和水果分别是什么？",      # 这轮验证记忆
]

for q in questions:
    messages.append({"role": "user", "content": q})
    response = client.chat.completions.create(
        model = "glm-4-flash",
        messages = messages #每次对话都要把之前的所有对话历史全都输入进去
    )
    resp = response.choices[0].message.content
    messages.append({"role" :"assistant", "content": resp})
    print(f"模型回答：{resp}\n")

response1 = client.chat.completions.create(
    model = "glm-4-flash",
    messages = [{"role": "user", "content": "我刚才说最喜欢的数字和水果分别是什么？"}]
)
resp1 = response1.choices[0].message
print(f"模型失忆回答：{resp1}\n")
