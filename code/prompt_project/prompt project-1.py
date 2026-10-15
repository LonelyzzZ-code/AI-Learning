import os
from pathlib import Path
from openai import OpenAI
import json

client = OpenAI(
    api_key = os.environ["ZHIPU_API_KEY"],
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

Files = ["File/01-LLM-API三件套.md", "File/02-Prompt工程.md"]
system_messages = [{"role": "system", "content": "你是文章分析器。只输出 JSON，格式 {title, tags, summary}，不要其他文字"}]
results = {}

for path in Files:
    with open(path, "r", encoding = "utf-8") as f:
              content = f.read()
    base_messages = system_messages + [{"role": "user", "content": content}]
    response = client.chat.completions.create(
        model = "glm-4-flash",
        messages = base_messages,
        response_format = {"type": "json_object"}
    )
    resp = response.choices[0].message.content
    try:
        data = json.loads(resp)
    except json.JSONDecodeError:
        base_messages = base_messages + [
            {"role": "assistant", "content": resp},
            {"role": "user", "content": "上面的输出不是合法JSON，请严格只输出JSON"}
        ]
        resp1 = client.chat.completions.create(
            model = "glm-4-flash",
            messages = base_messages,
            response_format = {"type": "json_object"}
        ).choices[0].message.content
        data = json.loads(resp1)
    results[path] = {                         # ← 改动2：缩进进循环体，跟 try 对齐
        "title": data.get("title", ""),
        "tags": data.get("tags", []),
        "summary": data.get("summary", "")
    }
out_path = Path(__file__).resolve().parent / "text" / "text3.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("写入完毕！")