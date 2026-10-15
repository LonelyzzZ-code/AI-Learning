import json
import os
from openai import OpenAI

client = OpenAI(
    api_key = os.environ["ZHIPU_API_KEY"],
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

with open("File/01-LLM-API三件套.md", encoding = "utf-8") as f:
    content = f.read()

for m in [0.1,0.9]:
    for i in range(3):
        response = client.chat.completions.create(
            model = "glm-4-flash",
            messages = [
                {"role": "system", "content": content},
                {"role": "user", "content": "请用一句话总结这篇文章"}
            ],
            temperature = m
        )
        resp = response.choices[0].message.content
        print(f"这是第{i+1}次输出的结果为：{resp}\ntemperature为：{m}")