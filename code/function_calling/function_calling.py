import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["ZHIPU_API_KEY"],
                base_url="https://open.bigmodel.cn/api/paas/v4/")

json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "function-calling-tools.json")
with open(json_path, encoding="utf-8") as f:
    tools = json.load(f)

resp = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": "深圳今天天气怎么样？"}],
    tools=tools,
)
msg = resp.choices[0].message

if msg.tool_calls:
    call = msg.tool_calls[0]
    args = json.loads(call.function.arguments)
    result = {"city": args["city"], "temp": "30°C", "cond": "晴"}

    final = client.chat.completions.create(
        model="glm-4-flash",
        messages=[
            {"role": "user", "content": "深圳今天天气怎么样？"},
            msg,
            {"role": "tool", "tool_call_id": call.id,
             "content": json.dumps(result, ensure_ascii=False)},
        ],
    )
    print(final.choices[0].message.content)
